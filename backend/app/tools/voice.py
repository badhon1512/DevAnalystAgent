import mimetypes
import os
import shutil
import tempfile
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel


ELEVENLABS_API_BASE = "https://api.elevenlabs.io/v1"


class VoiceTranscription(BaseModel):
    transcript: str
    model: str
    latency_ms: int


@dataclass(frozen=True)
class SynthesizedSpeech:
    content: bytes
    content_type: str
    model: str


class VoiceTranscriptionUnavailable(RuntimeError):
    pass


class VoiceSynthesisUnavailable(RuntimeError):
    pass


def voice_transcription_enabled() -> bool:
    return os.getenv("VOICE_TRANSCRIPTION_ENABLED", "true").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def asr_provider() -> str:
    return os.getenv("VOICE_ASR_PROVIDER", "elevenlabs").strip().lower()


def tts_provider() -> str:
    return os.getenv("VOICE_TTS_PROVIDER", "elevenlabs").strip().lower()


def whisper_model_name() -> str:
    return os.getenv("WHISPER_MODEL", "base")


def _elevenlabs_api_key(error_type: type[RuntimeError]) -> str:
    api_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    if not api_key:
        raise error_type("ELEVENLABS_API_KEY is required for the ElevenLabs voice provider.")
    return api_key


def _elevenlabs_error(response: httpx.Response, operation: str) -> str:
    try:
        payload = response.json()
        detail = payload.get("detail") if isinstance(payload, dict) else None
        if isinstance(detail, dict):
            detail = detail.get("message") or detail.get("status")
        if detail:
            return f"ElevenLabs {operation} failed: {detail}"
    except ValueError:
        pass
    return f"ElevenLabs {operation} failed with status {response.status_code}."


def _prepend_to_path(directory: Path) -> None:
    current = os.environ.get("PATH", "")
    parts = current.split(os.pathsep) if current else []
    directory_str = str(directory)
    if directory_str not in parts:
        os.environ["PATH"] = directory_str + os.pathsep + current if current else directory_str


def _ensure_ffmpeg_available() -> None:
    if shutil.which("ffmpeg"):
        return

    configured = os.getenv("FFMPEG_BINARY", "").strip()
    if configured:
        configured_path = Path(configured)
        if configured_path.exists():
            _prepend_to_path(configured_path.parent)
            if shutil.which("ffmpeg"):
                return

    local_app_data = os.getenv("LOCALAPPDATA", "").strip()
    if local_app_data:
        root = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"
        candidates = sorted(root.glob("Gyan.FFmpeg_*/*/bin/ffmpeg.exe"))
        if candidates:
            _prepend_to_path(candidates[-1].parent)
            if shutil.which("ffmpeg"):
                return

    raise VoiceTranscriptionUnavailable(
        "ffmpeg was not found. Install ffmpeg and make sure it is available on PATH."
    )


@lru_cache(maxsize=1)
def _load_whisper_model(model_name: str) -> Any:
    try:
        import whisper
    except ImportError as exc:
        raise VoiceTranscriptionUnavailable(
            "Whisper is not installed. Install the voice extras and ensure ffmpeg is available."
        ) from exc

    return whisper.load_model(model_name)


def _transcribe_with_whisper(path: Path) -> VoiceTranscription:
    model_name = whisper_model_name()
    model = _load_whisper_model(model_name)
    started = time.perf_counter()
    _ensure_ffmpeg_available()
    try:
        result = model.transcribe(str(path), fp16=False)
    except FileNotFoundError as exc:
        raise VoiceTranscriptionUnavailable(
            "ffmpeg was not found. Install ffmpeg and make sure it is available on PATH."
        ) from exc

    return VoiceTranscription(
        transcript=str(result.get("text", "")).strip(),
        model=f"whisper-{model_name}",
        latency_ms=int((time.perf_counter() - started) * 1000),
    )


def _transcribe_with_elevenlabs(
    path: Path,
    content_type: str | None,
    client: httpx.Client | None = None,
) -> VoiceTranscription:
    model = os.getenv("VOICE_ASR_MODEL", "scribe_v2").strip() or "scribe_v2"
    language = os.getenv("VOICE_ASR_LANGUAGE", "").strip()
    data = {
        "model_id": model,
        "tag_audio_events": "false",
        "diarize": "false",
    }
    if language:
        data["language_code"] = language

    media_type = content_type or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    started = time.perf_counter()
    owns_client = client is None
    http_client = client or httpx.Client(timeout=httpx.Timeout(60.0, connect=10.0))
    try:
        with path.open("rb") as audio_file:
            response = http_client.post(
                f"{ELEVENLABS_API_BASE}/speech-to-text",
                headers={
                    "xi-api-key": _elevenlabs_api_key(VoiceTranscriptionUnavailable),
                },
                data=data,
                files={"file": (path.name, audio_file, media_type)},
            )
    except httpx.HTTPError as exc:
        raise VoiceTranscriptionUnavailable(
            "ElevenLabs transcription could not be reached."
        ) from exc
    finally:
        if owns_client:
            http_client.close()

    if not response.is_success:
        raise VoiceTranscriptionUnavailable(_elevenlabs_error(response, "transcription"))

    payload = response.json()
    return VoiceTranscription(
        transcript=str(payload.get("text", "")).strip(),
        model=model,
        latency_ms=int((time.perf_counter() - started) * 1000),
    )


def transcribe_audio_file(
    path: Path,
    content_type: str | None = None,
    client: httpx.Client | None = None,
) -> VoiceTranscription:
    if not voice_transcription_enabled():
        raise VoiceTranscriptionUnavailable(
            "Voice transcription is disabled. Set VOICE_TRANSCRIPTION_ENABLED=true to enable it."
        )

    provider = asr_provider()
    if provider == "elevenlabs":
        return _transcribe_with_elevenlabs(path, content_type, client)
    if provider == "whisper":
        return _transcribe_with_whisper(path)
    raise VoiceTranscriptionUnavailable(
        f"Unsupported voice transcription provider: {provider}."
    )


def transcribe_audio_bytes(
    content: bytes,
    suffix: str = ".webm",
    content_type: str | None = None,
    client: httpx.Client | None = None,
) -> VoiceTranscription:
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        return transcribe_audio_file(tmp_path, content_type=content_type, client=client)
    finally:
        tmp_path.unlink(missing_ok=True)


def synthesize_speech(
    text: str,
    client: httpx.Client | None = None,
) -> SynthesizedSpeech:
    provider = tts_provider()
    if provider != "elevenlabs":
        raise VoiceSynthesisUnavailable(
            f"Unsupported voice synthesis provider: {provider}."
        )

    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "").strip()
    if not voice_id:
        raise VoiceSynthesisUnavailable(
            "ELEVENLABS_VOICE_ID is required for ElevenLabs speech synthesis."
        )

    model = os.getenv("VOICE_TTS_MODEL", "eleven_flash_v2_5").strip() or "eleven_flash_v2_5"
    output_format = os.getenv("VOICE_TTS_OUTPUT_FORMAT", "mp3_44100_128").strip()
    owns_client = client is None
    http_client = client or httpx.Client(timeout=httpx.Timeout(60.0, connect=10.0))
    try:
        response = http_client.post(
            f"{ELEVENLABS_API_BASE}/text-to-speech/{voice_id}",
            params={"output_format": output_format},
            headers={
                "xi-api-key": _elevenlabs_api_key(VoiceSynthesisUnavailable),
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
            },
            json={"text": text, "model_id": model},
        )
    except httpx.HTTPError as exc:
        raise VoiceSynthesisUnavailable(
            "ElevenLabs speech synthesis could not be reached."
        ) from exc
    finally:
        if owns_client:
            http_client.close()

    if not response.is_success:
        raise VoiceSynthesisUnavailable(_elevenlabs_error(response, "speech synthesis"))

    return SynthesizedSpeech(
        content=response.content,
        content_type=response.headers.get("content-type", "audio/mpeg").split(";")[0],
        model=model,
    )

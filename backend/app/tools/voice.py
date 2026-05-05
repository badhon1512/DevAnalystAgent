import os
import shutil
import tempfile
import time
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel


class VoiceTranscription(BaseModel):
    transcript: str
    model: str
    latency_ms: int


class VoiceTranscriptionUnavailable(RuntimeError):
    pass


def voice_transcription_enabled() -> bool:
    return os.getenv("VOICE_TRANSCRIPTION_ENABLED", "false").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def whisper_model_name() -> str:
    return os.getenv("WHISPER_MODEL", "base")


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


def transcribe_audio_file(path: Path) -> VoiceTranscription:
    if not voice_transcription_enabled():
        raise VoiceTranscriptionUnavailable(
            "Voice transcription is disabled. Set VOICE_TRANSCRIPTION_ENABLED=true to enable it."
        )

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
    latency_ms = int((time.perf_counter() - started) * 1000)

    return VoiceTranscription(
        transcript=str(result.get("text", "")).strip(),
        model=f"whisper-{model_name}",
        latency_ms=latency_ms,
    )


def transcribe_audio_bytes(content: bytes, suffix: str = ".webm") -> VoiceTranscription:
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        return transcribe_audio_file(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)

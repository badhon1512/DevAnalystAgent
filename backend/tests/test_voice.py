import httpx

from app.tools.voice import (
    VoiceSynthesisUnavailable,
    VoiceTranscription,
    synthesize_speech,
    transcribe_audio_bytes,
)


def test_elevenlabs_is_default_asr_provider(monkeypatch):
    monkeypatch.delenv("VOICE_ASR_PROVIDER", raising=False)
    monkeypatch.setenv("VOICE_TRANSCRIPTION_ENABLED", "true")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/speech-to-text"
        assert request.headers["xi-api-key"] == "test-key"
        assert b'scribe_v2' in request.content
        assert b'audio-data' in request.content
        return httpx.Response(200, json={"text": "Show branch demand"})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = transcribe_audio_bytes(
            b"audio-data",
            suffix=".webm",
            content_type="audio/webm",
            client=client,
        )

    assert result.transcript == "Show branch demand"
    assert result.model == "scribe_v2"
    assert result.latency_ms >= 0


def test_whisper_remains_an_optional_asr_provider(monkeypatch):
    monkeypatch.setenv("VOICE_ASR_PROVIDER", "whisper")
    monkeypatch.setenv("VOICE_TRANSCRIPTION_ENABLED", "true")
    expected = VoiceTranscription(
        transcript="Local transcription",
        model="whisper-base",
        latency_ms=12,
    )
    monkeypatch.setattr("app.tools.voice._transcribe_with_whisper", lambda _path: expected)

    result = transcribe_audio_bytes(b"audio-data")

    assert result == expected


def test_elevenlabs_tts_returns_audio(monkeypatch):
    monkeypatch.delenv("VOICE_TTS_PROVIDER", raising=False)
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")
    monkeypatch.setenv("ELEVENLABS_VOICE_ID", "voice-123")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/text-to-speech/voice-123"
        assert request.url.params["output_format"] == "mp3_44100_128"
        assert request.headers["xi-api-key"] == "test-key"
        assert b'eleven_flash_v2_5' in request.content
        assert b'Inventory is healthy' in request.content
        return httpx.Response(
            200,
            content=b"mp3-audio",
            headers={"content-type": "audio/mpeg"},
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = synthesize_speech("Inventory is healthy", client=client)

    assert result.content == b"mp3-audio"
    assert result.content_type == "audio/mpeg"
    assert result.model == "eleven_flash_v2_5"


def test_elevenlabs_tts_requires_voice_id(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")
    monkeypatch.delenv("ELEVENLABS_VOICE_ID", raising=False)

    try:
        synthesize_speech("Hello")
    except VoiceSynthesisUnavailable as exc:
        assert "ELEVENLABS_VOICE_ID" in str(exc)
    else:
        raise AssertionError("Expected missing ElevenLabs voice ID to be rejected")

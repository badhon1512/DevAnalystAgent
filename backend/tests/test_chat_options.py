import pytest
from pydantic import ValidationError

from app.schemas.chat import ChatRequest


def test_chat_options_use_safe_defaults() -> None:
    request = ChatRequest(query="Show revenue", conversation_id="thread-1", username="demo_user")

    assert request.options.model == "gpt-5.4"
    assert request.options.analysis_depth == "balanced"
    assert request.options.answer_detail == "balanced"


def test_chat_options_accept_supported_values() -> None:
    request = ChatRequest(
        query="Investigate stock risk",
        conversation_id="thread-1",
        username="demo_user",
        options={
            "model": "gpt-4.1",
            "analysis_depth": "deep",
            "answer_detail": "detailed",
        },
    )

    assert request.options.model == "gpt-4.1"
    assert request.options.analysis_depth == "deep"
    assert request.options.answer_detail == "detailed"


def test_chat_options_reject_unknown_model() -> None:
    with pytest.raises(ValidationError):
        ChatRequest(
            query="Show revenue",
            conversation_id="thread-1",
            username="demo_user",
            options={"model": "unapproved-model"},
        )

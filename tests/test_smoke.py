"""Smoke tests for UnisonMemory — no network required."""

from __future__ import annotations

import json
from typing import Any, Dict, Generator
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ingest_response(job_id: str = "job-abc-123") -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"items": [{"type": "conversation", "jobId": job_id}]}
    return resp


def _make_recall_response(context_md: str = "## Memory\nYou met Alice last week.") -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {
        "query": "test query",
        "mode": "auto",
        "topScore": 0.85,
        "weakEvidence": False,
        "hits": [
            {
                "doc": {"path": "/private/person/alice.md", "title": "Alice"},
                "score": 0.85,
                "highlight": "You met Alice last week.",
            }
        ],
        "entities": [],
        "contextMd": context_md,
    }
    return resp


def _make_weak_recall_response() -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {
        "query": "unknown topic",
        "mode": "auto",
        "topScore": None,
        "weakEvidence": True,
        "hits": [],
        "entities": [],
        "contextMd": "",
    }
    return resp


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_httpx_client() -> Generator[MagicMock, None, None]:
    """Patch httpx.Client so no real HTTP calls are made."""
    with patch("llama_index.memory.unison._client.httpx.Client") as mock_cls:
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance
        yield mock_instance


# ---------------------------------------------------------------------------
# Tests: put() POSTs to /v1/brain/ingest
# ---------------------------------------------------------------------------

class TestPut:
    def test_put_posts_to_ingest(self, mock_httpx_client: MagicMock) -> None:
        from llama_index.core.base.llms.types import ChatMessage, MessageRole
        from llama_index.memory.unison import UnisonMemory

        mock_httpx_client.post.return_value = _make_ingest_response()

        mem = UnisonMemory.from_defaults(
            session_id="session-42",
            api_key="usk_live_test",
        )
        msg = ChatMessage(role=MessageRole.USER, content="Hello, world!")
        mem.put(msg)

        mock_httpx_client.post.assert_called_once()
        call_args = mock_httpx_client.post.call_args

        # First positional arg is the URL
        url: str = call_args[0][0]
        assert url.endswith("/v1/brain/ingest"), f"Expected /v1/brain/ingest, got {url}"

        # Body JSON is in `json` kwarg
        body: Dict[str, Any] = call_args[1]["json"]
        assert "items" in body
        assert len(body["items"]) == 1
        item = body["items"][0]
        assert item["type"] == "conversation"
        assert item["sourceRef"] == "session-42"
        assert item["visibility"] == "private"
        assert len(item["turns"]) == 1
        assert item["turns"][0]["role"] == "user"
        assert item["turns"][0]["content"] == "Hello, world!"

    def test_put_adds_to_buffer(self, mock_httpx_client: MagicMock) -> None:
        from llama_index.core.base.llms.types import ChatMessage, MessageRole
        from llama_index.memory.unison import UnisonMemory

        mock_httpx_client.post.return_value = _make_ingest_response()

        mem = UnisonMemory.from_defaults(session_id="s1", api_key="usk_live_test")
        mem.put(ChatMessage(role=MessageRole.USER, content="turn 1"))
        mem.put(ChatMessage(role=MessageRole.ASSISTANT, content="turn 2"))

        all_msgs = mem.get_all()
        assert len(all_msgs) == 2
        assert all_msgs[0].content == "turn 1"
        assert all_msgs[1].content == "turn 2"

    def test_put_maps_assistant_role(self, mock_httpx_client: MagicMock) -> None:
        from llama_index.core.base.llms.types import ChatMessage, MessageRole
        from llama_index.memory.unison import UnisonMemory

        mock_httpx_client.post.return_value = _make_ingest_response()

        mem = UnisonMemory.from_defaults(session_id="s2", api_key="usk_live_test")
        mem.put(ChatMessage(role=MessageRole.ASSISTANT, content="I can help with that."))

        body = mock_httpx_client.post.call_args[1]["json"]
        assert body["items"][0]["turns"][0]["role"] == "assistant"

    def test_put_tolerates_ingest_failure(self, mock_httpx_client: MagicMock) -> None:
        """Network errors during ingest must not crash the caller."""
        from llama_index.core.base.llms.types import ChatMessage, MessageRole
        from llama_index.memory.unison import UnisonMemory

        mock_httpx_client.post.side_effect = Exception("connection refused")

        mem = UnisonMemory.from_defaults(session_id="s3", api_key="usk_live_test")
        # Should not raise
        mem.put(ChatMessage(role=MessageRole.USER, content="hello"))
        assert len(mem.get_all()) == 1


# ---------------------------------------------------------------------------
# Tests: get() calls /v1/brain/context and injects contextMd
# ---------------------------------------------------------------------------

class TestGet:
    def test_get_calls_context_endpoint(self, mock_httpx_client: MagicMock) -> None:
        from llama_index.core.base.llms.types import ChatMessage, MessageRole
        from llama_index.memory.unison import UnisonMemory

        mock_httpx_client.post.return_value = _make_ingest_response()
        mock_httpx_client.get.return_value = _make_recall_response()

        mem = UnisonMemory.from_defaults(session_id="s4", api_key="usk_live_test")
        mem.put(ChatMessage(role=MessageRole.USER, content="Who is Alice?"))

        messages = mem.get(input="Who is Alice?")

        mock_httpx_client.get.assert_called_once()
        url: str = mock_httpx_client.get.call_args[0][0]
        assert "/v1/brain/context" in url
        assert "q=" in url

    def test_get_injects_context_md_as_system_message(
        self, mock_httpx_client: MagicMock
    ) -> None:
        from llama_index.core.base.llms.types import ChatMessage, MessageRole
        from llama_index.memory.unison import UnisonMemory

        context_md = "## Memory\nYou met Alice last week."
        mock_httpx_client.post.return_value = _make_ingest_response()
        mock_httpx_client.get.return_value = _make_recall_response(context_md=context_md)

        mem = UnisonMemory.from_defaults(session_id="s5", api_key="usk_live_test")
        mem.put(ChatMessage(role=MessageRole.USER, content="Tell me about Alice."))

        messages = mem.get(input="Tell me about Alice.")

        # First message must be the injected system message
        assert len(messages) >= 2
        system_msg = messages[0]
        assert system_msg.role == MessageRole.SYSTEM
        assert context_md in (system_msg.content or "")

    def test_get_no_injection_on_weak_evidence(
        self, mock_httpx_client: MagicMock
    ) -> None:
        from llama_index.core.base.llms.types import ChatMessage, MessageRole
        from llama_index.memory.unison import UnisonMemory

        mock_httpx_client.post.return_value = _make_ingest_response()
        mock_httpx_client.get.return_value = _make_weak_recall_response()

        mem = UnisonMemory.from_defaults(session_id="s6", api_key="usk_live_test")
        mem.put(ChatMessage(role=MessageRole.USER, content="Random topic"))

        messages = mem.get(input="Random topic")

        # With weakEvidence=True, no system message injected
        system_msgs = [m for m in messages if m.role == MessageRole.SYSTEM]
        assert len(system_msgs) == 0

    def test_get_tolerates_recall_failure(self, mock_httpx_client: MagicMock) -> None:
        """Network errors during recall must not crash; return buffer only."""
        from llama_index.core.base.llms.types import ChatMessage, MessageRole
        from llama_index.memory.unison import UnisonMemory

        mock_httpx_client.post.return_value = _make_ingest_response()
        mock_httpx_client.get.side_effect = Exception("timeout")

        mem = UnisonMemory.from_defaults(session_id="s7", api_key="usk_live_test")
        mem.put(ChatMessage(role=MessageRole.USER, content="hello"))

        # Should not raise; should return buffer as-is
        messages = mem.get(input="hello")
        assert len(messages) == 1


# ---------------------------------------------------------------------------
# Tests: reset(), set(), get_all()
# ---------------------------------------------------------------------------

class TestBufferOperations:
    def test_reset_clears_buffer(self, mock_httpx_client: MagicMock) -> None:
        from llama_index.core.base.llms.types import ChatMessage, MessageRole
        from llama_index.memory.unison import UnisonMemory

        mock_httpx_client.post.return_value = _make_ingest_response()

        mem = UnisonMemory.from_defaults(session_id="s8", api_key="usk_live_test")
        mem.put(ChatMessage(role=MessageRole.USER, content="msg"))
        assert len(mem.get_all()) == 1

        mem.reset()
        assert mem.get_all() == []

    def test_set_replaces_buffer(self, mock_httpx_client: MagicMock) -> None:
        from llama_index.core.base.llms.types import ChatMessage, MessageRole
        from llama_index.memory.unison import UnisonMemory

        mock_httpx_client.post.return_value = _make_ingest_response()

        mem = UnisonMemory.from_defaults(session_id="s9", api_key="usk_live_test")
        mem.put(ChatMessage(role=MessageRole.USER, content="old msg"))

        new_msgs = [
            ChatMessage(role=MessageRole.USER, content="new msg 1"),
            ChatMessage(role=MessageRole.ASSISTANT, content="new msg 2"),
        ]
        mem.set(new_msgs)

        all_msgs = mem.get_all()
        assert len(all_msgs) == 2
        assert all_msgs[0].content == "new msg 1"

    def test_class_name(self) -> None:
        from llama_index.memory.unison import UnisonMemory
        assert UnisonMemory.class_name() == "UnisonMemory"

    def test_from_client_alias(self, mock_httpx_client: MagicMock) -> None:
        from llama_index.memory.unison import UnisonMemory
        mem = UnisonMemory.from_client(session_id="alias-test", api_key="usk_live_test")
        assert mem.session_id == "alias-test"

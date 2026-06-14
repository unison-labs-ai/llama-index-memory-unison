"""UnisonMemory — LlamaIndex BaseMemory backed by the Unison brain."""

from __future__ import annotations

import os
import logging
from typing import Any, Dict, List, Optional

from llama_index.core.base.llms.types import ChatMessage, MessageRole
from llama_index.core.memory.types import BaseMemory
from pydantic import Field, PrivateAttr

from ._client import UnisonBrainClient, _DEFAULT_API_URL

logger = logging.getLogger(__name__)

_ROLE_TO_UNISON: Dict[str, str] = {
    MessageRole.USER.value: "user",
    MessageRole.ASSISTANT.value: "assistant",
    MessageRole.SYSTEM.value: "system",
    # treat tool/function turns as assistant for ingestion purposes
    MessageRole.TOOL.value: "assistant",
    MessageRole.FUNCTION.value: "assistant",
    # provider-specific aliases
    "chatbot": "assistant",
    "model": "assistant",
    "developer": "system",
}


def _role_str(msg: ChatMessage) -> str:
    """Map a ChatMessage role to the string Unison expects."""
    role_val = msg.role.value if isinstance(msg.role, MessageRole) else str(msg.role)
    return _ROLE_TO_UNISON.get(role_val, "user")


def _content_str(msg: ChatMessage) -> str:
    """Extract text content from a ChatMessage."""
    return msg.content or ""


class UnisonMemory(BaseMemory):
    """LlamaIndex memory that persists conversation turns to the Unison brain.

    Long-term memories are recalled on every ``get()`` call and injected as a
    system message ahead of the local chat buffer — identical in spirit to how
    ``Mem0Memory`` injects Mem0 context.

    Parameters
    ----------
    session_id:
        Stable identifier for the conversation/user session. Used as
        ``sourceRef`` in ingestion calls so the brain can group turns.
    api_key:
        Unison API token (``usk_live_...``). Defaults to the ``UNISON_TOKEN``
        environment variable.
    api_url:
        Base URL for the Unison brain. Defaults to the ``UNISON_API_URL``
        environment variable or ``https://brain.unisonlabs.ai``.
    search_k:
        Number of memory hits to request on recall. Default: 5.
    """

    # Pydantic fields (serialisable, so the object can be model_dump()'d)
    session_id: str = Field(description="Stable conversation / session identifier.")
    api_key: str = Field(
        default="",
        description="Unison API token. Falls back to UNISON_TOKEN env var.",
        exclude=True,  # never serialise credentials
    )
    api_url: str = Field(
        default=_DEFAULT_API_URL,
        description="Unison brain base URL.",
    )
    search_k: int = Field(default=5, description="Hits requested per recall call.")

    # Non-serialised runtime state
    _buffer: List[ChatMessage] = PrivateAttr(default_factory=list)
    _client: Optional[UnisonBrainClient] = PrivateAttr(default=None)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_client(self) -> UnisonBrainClient:
        """Lazily initialise the HTTP client."""
        if self._client is None:
            key = self.api_key or os.environ.get("UNISON_TOKEN", "")
            url = self.api_url or os.environ.get("UNISON_API_URL", _DEFAULT_API_URL)
            if not key:
                raise ValueError(
                    "Unison API key is required. Pass api_key= or set the "
                    "UNISON_TOKEN environment variable."
                )
            self._client = UnisonBrainClient(api_key=key, api_url=url)
        return self._client

    def _ingest_message(self, msg: ChatMessage) -> None:
        """Fire-and-forget ingest of a single turn to Unison."""
        content = _content_str(msg)
        if not content:
            return
        turn = {"role": _role_str(msg), "content": content}
        try:
            client = self._get_client()
            client.ingest_conversation(turns=[turn], source_ref=self.session_id)
        except Exception as exc:
            logger.warning("UnisonMemory: ingest error (continuing): %s", exc)

    def _recall_context(self, query: str) -> Optional[str]:
        """Return contextMd from the brain, or None if weak/unavailable."""
        try:
            client = self._get_client()
            result = client.recall(query=query, k=self.search_k)
            if result is None:
                return None
            if result.get("weakEvidence", True):
                return None
            return result.get("contextMd") or None
        except Exception as exc:
            logger.warning("UnisonMemory: recall error (continuing): %s", exc)
            return None

    def _last_user_text(self) -> str:
        """Return the content of the most recent user turn in the buffer."""
        for msg in reversed(self._buffer):
            if msg.role == MessageRole.USER:
                return _content_str(msg)
        return ""

    # ------------------------------------------------------------------
    # BaseMemory abstract interface
    # ------------------------------------------------------------------

    @classmethod
    def class_name(cls) -> str:
        return "UnisonMemory"

    @classmethod
    def from_defaults(
        cls,
        session_id: str = "default",
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        search_k: int = 5,
        **kwargs: Any,
    ) -> "UnisonMemory":
        """Create a UnisonMemory with sensible defaults.

        Parameters
        ----------
        session_id:
            Conversation identifier, e.g. ``"user-123"``.
        api_key:
            Unison API token. Defaults to ``UNISON_TOKEN`` env var.
        api_url:
            Unison brain URL. Defaults to ``UNISON_API_URL`` env var or
            ``https://brain.unisonlabs.ai``.
        search_k:
            Hits per recall. Default: 5.
        """
        return cls(
            session_id=session_id,
            api_key=api_key or os.environ.get("UNISON_TOKEN", ""),
            api_url=api_url or os.environ.get("UNISON_API_URL", _DEFAULT_API_URL),
            search_k=search_k,
            **kwargs,
        )

    # Convenience alias used in most documentation examples
    from_client = from_defaults  # type: ignore[assignment]

    def get(
        self,
        input: Optional[str] = None,
        **kwargs: Any,
    ) -> List[ChatMessage]:
        """Return local buffer prepended with a Unison memory system message.

        The recall query is ``input`` (the incoming user message) if provided,
        otherwise the most recent user turn in the buffer.  If the brain
        returns ``weakEvidence=true`` (nothing relevant), no system message is
        injected and only the local buffer is returned.
        """
        query = input or self._last_user_text()
        messages: List[ChatMessage] = list(self._buffer)

        if query:
            context_md = self._recall_context(query)
            if context_md:
                memory_msg = ChatMessage(
                    role=MessageRole.SYSTEM,
                    content=(
                        "## Relevant long-term memory (from Unison brain)\n\n"
                        + context_md
                    ),
                )
                messages = [memory_msg] + messages

        return messages

    def get_all(self) -> List[ChatMessage]:
        """Return the raw local buffer (no recall)."""
        return list(self._buffer)

    def put(self, message: ChatMessage) -> None:
        """Append a message to the buffer and ingest it to Unison."""
        self._buffer.append(message)
        self._ingest_message(message)

    def set(self, messages: List[ChatMessage]) -> None:
        """Replace the local buffer. Does not modify server memory."""
        self._buffer = list(messages)

    def reset(self) -> None:
        """Clear the local buffer. Does not delete server memory."""
        self._buffer = []

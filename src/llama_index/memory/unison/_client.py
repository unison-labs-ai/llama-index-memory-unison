"""HTTP client for the Unison brain API."""

from __future__ import annotations

import logging
import urllib.parse
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

_DEFAULT_API_URL = "https://brain.unisonlabs.ai"
_DEFAULT_TIMEOUT = 15.0


class UnisonBrainClient:
    """Minimal synchronous client for the Unison brain /v1 API.

    Parameters
    ----------
    api_key:
        Unison API token (``usk_live_...``). Falls back to the
        ``UNISON_TOKEN`` environment variable.
    api_url:
        Base URL of the brain service. Falls back to ``UNISON_API_URL``
        or ``https://brain.unisonlabs.ai``.
    timeout:
        HTTP timeout in seconds. Default: 15.
    """

    def __init__(
        self,
        api_key: str,
        api_url: str = _DEFAULT_API_URL,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self._base = api_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        self._client = httpx.Client(
            timeout=timeout,
            headers=self._headers,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def ingest_conversation(
        self,
        turns: List[Dict[str, str]],
        source_ref: str,
    ) -> Optional[str]:
        """POST /v1/brain/ingest — async on the server, returns jobId.

        Parameters
        ----------
        turns:
            List of ``{"role": "user|assistant|system", "content": "..."}``.
        source_ref:
            Session / thread identifier used as ``sourceRef``.

        Returns
        -------
        Job ID string, or ``None`` if the call failed.
        """
        payload: Dict[str, Any] = {
            "items": [
                {
                    "type": "conversation",
                    "turns": turns,
                    "sourceRef": source_ref,
                    "visibility": "private",
                }
            ]
        }
        try:
            resp = self._client.post(f"{self._base}/v1/brain/ingest", json=payload)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            if results:
                return results[0].get("jobId")
        except Exception as exc:
            logger.warning("Unison ingest failed (degrading gracefully): %s", exc)
        return None

    def recall(
        self,
        query: str,
        k: int = 5,
        mode: str = "auto",
    ) -> Optional[Dict[str, Any]]:
        """GET /v1/brain/context — returns the full recall payload.

        Parameters
        ----------
        query:
            Natural-language query.
        k:
            Number of hits requested.
        mode:
            Recall mode, default ``"auto"``.

        Returns
        -------
        Parsed JSON dict, or ``None`` if the call failed.
        """
        params = {
            "q": query,
            "k": str(k),
            "mode": mode,
        }
        url = f"{self._base}/v1/brain/context?" + urllib.parse.urlencode(params)
        try:
            resp = self._client.get(url)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            logger.warning("Unison recall failed (degrading gracefully): %s", exc)
        return None

    def search(
        self,
        query: str,
        k: int = 5,
    ) -> Optional[Dict[str, Any]]:
        """GET /v1/brain/search — ranked keyword/semantic search.

        Parameters
        ----------
        query:
            Search query.
        k:
            Number of results requested.

        Returns
        -------
        Parsed JSON dict, or ``None`` if the call failed.
        """
        params = {"q": query, "k": str(k)}
        url = f"{self._base}/v1/brain/search?" + urllib.parse.urlencode(params)
        try:
            resp = self._client.get(url)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            logger.warning("Unison search failed (degrading gracefully): %s", exc)
        return None

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    def __enter__(self) -> "UnisonBrainClient":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

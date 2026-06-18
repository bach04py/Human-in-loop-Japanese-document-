"""Document Q&A chatbot powered by Qwen2.5 (served by Ollama).

Answers are grounded strictly in a single extracted document's JSON, which is
loaded from :mod:`app.services.document_store`.
"""

import json
import logging
import os
from typing import Any

import httpx

from app.schemas import ChatMessage

logger = logging.getLogger(__name__)

# Keep the most recent turns so follow-up questions have context without
# blowing past the model's context window.
MAX_HISTORY_TURNS = 8

SYSTEM_PROMPT = (
    "You are a helpful assistant that answers questions about ONE extracted "
    "document. The document's structured data is provided below as JSON.\n"
    "Rules:\n"
    "- Use ONLY the document JSON as your source of truth.\n"
    "- If the answer is not present in the document, say you don't have that "
    "information rather than guessing.\n"
    "- Be concise and factual. Reply in the same language as the user "
    "(Japanese or English)."
)


class ChatService:
    """Generates grounded answers about a stored document using Qwen2.5."""

    def __init__(self) -> None:
        self.local_llm_url = os.environ.get(
            "LLM_ENDPOINT", "http://127.0.0.1:11434/api/generate"
        )
        self.model_name = os.environ.get("LLM_MODEL", "qwen2.5")
        self.timeout_seconds = float(os.environ.get("LLM_TIMEOUT_SECONDS", "60"))

    def _build_prompt(
        self, document: dict[str, Any], message: str, history: list[ChatMessage]
    ) -> str:
        document_json = json.dumps(document, ensure_ascii=False, indent=2)

        history_lines = []
        for turn in history[-MAX_HISTORY_TURNS:]:
            speaker = "User" if turn.role == "user" else "Assistant"
            history_lines.append(f"{speaker}: {turn.content}")
        conversation = "\n".join(history_lines)

        return (
            f"{SYSTEM_PROMPT}\n\n"
            f"=== DOCUMENT JSON ===\n{document_json}\n\n"
            f"=== CONVERSATION SO FAR ===\n{conversation}\n\n"
            f"User: {message}\nAssistant:"
        )

    async def answer(
        self,
        document: dict[str, Any],
        message: str,
        history: list[ChatMessage] | None = None,
    ) -> str:
        prompt = self._build_prompt(document, message, history or [])

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.2, "top_p": 0.9},
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(self.local_llm_url, json=payload)
                response.raise_for_status()
                result = response.json()
                reply = result.get("response", "").strip()
                return reply or "I couldn't generate a response for that question."
        except httpx.TimeoutException:
            logger.warning("Chat LLM timed out for the document Q&A request.")
            return "The model took too long to respond. Please try asking again."
        except httpx.HTTPError as exc:
            logger.warning("Chat LLM unavailable: %s", exc)
            return (
                "The chat model is unavailable. Make sure the local LLM "
                "(Ollama running qwen2.5) is started and try again."
            )

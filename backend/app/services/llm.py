"""Client for the local Ollama server (chat + vision)."""
import base64
import json
import logging
import re
from pathlib import Path

import requests

from app.config import OLLAMA_MODEL, OLLAMA_NUM_CTX, OLLAMA_TIMEOUT_SEC, OLLAMA_URL

logger = logging.getLogger("meetingiq.llm")


class LLMError(RuntimeError):
    pass


def _parse_json(content: str) -> dict:
    """Parse model output as a JSON object, tolerating <think> blocks and stray text."""
    text = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise LLMError("Model did not return a JSON object.")
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise LLMError(f"Model returned invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise LLMError("Model returned JSON that is not an object.")
    return data


def chat_json(prompt: str, image_paths: list[Path] | None = None) -> tuple[dict, str]:
    """Send a prompt (optionally with images) and return (parsed JSON, raw text)."""
    message: dict = {"role": "user", "content": prompt}
    if image_paths:
        message["images"] = [
            base64.b64encode(p.read_bytes()).decode("ascii") for p in image_paths
        ]

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [message],
        "format": "json",
        "stream": False,
        "think": False,  # no reasoning text before the JSON
        "options": {"temperature": 0.2, "num_ctx": OLLAMA_NUM_CTX},
    }
    try:
        resp = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=OLLAMA_TIMEOUT_SEC)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise LLMError(
            f"Could not reach Ollama at {OLLAMA_URL} (is it running, and is '{OLLAMA_MODEL}' pulled?): {exc}"
        ) from exc

    raw = resp.json().get("message", {}).get("content", "")
    return _parse_json(raw), raw


def chat_json_with_retry(prompt: str, image_paths: list[Path] | None = None,
                         attempts: int = 2) -> tuple[dict, str]:
    """Retry once when the model returns invalid JSON (small models sometimes do)."""
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return chat_json(prompt, image_paths)
        except LLMError as exc:
            last_error = exc
            logger.warning("LLM attempt %d/%d failed: %s", attempt, attempts, exc)
    raise LLMError(str(last_error))

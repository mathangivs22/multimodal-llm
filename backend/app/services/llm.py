"""Client for the local Ollama server (chat + vision)."""
import base64
import json
import logging
import re
import time
from pathlib import Path

import requests

from app.config import OLLAMA_NUM_CTX, OLLAMA_NUM_PREDICT, OLLAMA_TIMEOUT_SEC, OLLAMA_URL

logger = logging.getLogger("meetingiq.llm")


class LLMError(RuntimeError):
    pass


class LLMTruncated(LLMError):
    """The reply hit the token cap. Retrying the same request would hit it again."""


def _parse_json(content: str) -> dict:
    """Parse model output as a JSON object, tolerating <think> blocks and stray text."""
    text = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise LLMError(f"Model did not return a JSON object. Start of reply: {text[:300]!r}")
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise LLMError(f"Model returned invalid JSON: {exc}. Start of reply: {text[:300]!r}") from exc
    if not isinstance(data, dict):
        raise LLMError("Model returned JSON that is not an object.")
    return data


def chat_json(prompt: str, image_paths: list[Path] | None, model: str, label: str,
              num_predict: int) -> tuple[dict, str]:
    """Send a prompt (optionally with images) and return (parsed JSON, raw text)."""
    message: dict = {"role": "user", "content": prompt}
    if image_paths:
        message["images"] = [
            base64.b64encode(p.read_bytes()).decode("ascii") for p in image_paths
        ]

    payload = {
        "model": model,
        "messages": [message],
        "format": "json",
        "stream": False,
        "think": False,  # no reasoning text before the JSON
        "options": {
            "temperature": 0.2,
            "num_ctx": OLLAMA_NUM_CTX,
            "num_predict": num_predict,  # hard cap on reply length
        },
    }
    started = time.time()
    logger.info("[%s] sending request to %s (prompt %d chars, %d image(s))",
                label, model, len(prompt), len(image_paths or []))
    try:
        resp = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=OLLAMA_TIMEOUT_SEC)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise LLMError(
            f"Could not reach Ollama at {OLLAMA_URL} (is it running, and is '{model}' pulled?): {exc}"
        ) from exc

    body = resp.json()
    raw = body.get("message", {}).get("content", "")
    done_reason = body.get("done_reason")
    logger.info("[%s] reply in %.1fs: %d chars, done_reason=%s",
                label, time.time() - started, len(raw), done_reason)
    if done_reason == "length":
        raise LLMTruncated(f"{label}: reply hit the {num_predict}-token cap before finishing.")
    return _parse_json(raw), raw


def chat_json_with_retry(prompt: str, image_paths: list[Path] | None = None, *,
                         model: str, label: str, num_predict: int = OLLAMA_NUM_PREDICT,
                         attempts: int = 2) -> tuple[dict, str]:
    """Retry once when the reply is invalid JSON, but never retry a truncated reply."""
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return chat_json(prompt, image_paths, model, label, num_predict)
        except LLMTruncated:
            raise
        except LLMError as exc:
            last_error = exc
            logger.warning("[%s] attempt %d/%d failed: %s", label, attempt, attempts, exc)
    raise LLMError(str(last_error))

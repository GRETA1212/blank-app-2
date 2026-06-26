import json
import os
import re
from typing import Any, TypeVar

import httpx
from fastapi import HTTPException
from pydantic import BaseModel, ValidationError

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")
T = TypeVar("T", bound=BaseModel)


def extract_json(text: str) -> Any:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        starts = [index for index in (cleaned.find("{"), cleaned.find("[")) if index >= 0]
        if not starts:
            raise ValueError("No JSON object found in model output")
        start = min(starts)
        closing = "}" if cleaned[start] == "{" else "]"
        end = cleaned.rfind(closing)
        if end <= start:
            raise ValueError("Incomplete JSON in model output")
        return json.loads(cleaned[start : end + 1])


async def chat_text(
    prompt: str,
    system: str,
    temperature: float = 0.3,
    timeout: float = 240,
) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "stream": False,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "options": {"temperature": temperature},
    }
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Local AI service is unavailable") from exc

    data = response.json()
    content = data.get("message", {}).get("content")
    if not isinstance(content, str) or not content.strip():
        raise HTTPException(status_code=502, detail="Local AI returned an empty response")
    return content.strip()


async def chat_json(
    prompt: str,
    system: str,
    schema: type[T],
    temperature: float = 0.2,
    timeout: float = 300,
) -> T:
    text = await chat_text(prompt, system, temperature, timeout)
    try:
        payload = extract_json(text)
        return schema.model_validate(payload)
    except (ValueError, json.JSONDecodeError, ValidationError) as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Local AI returned invalid structured output: {exc}",
        ) from exc

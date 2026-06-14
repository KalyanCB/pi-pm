from __future__ import annotations

import json
from typing import Any

import httpx

from app.args.llm.port import LlmCompletion


class OpenAiCompatibleLlmPort:
    """Chat-completions client for OpenAI-compatible APIs (OpenAI, Azure, vLLM, gateways)."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: int = 60,
        extra_headers: dict[str, str] | None = None,
        request_overrides: dict[str, Any] | None = None,
        text_mode: bool = False,
    ) -> None:
        if not api_key:
            raise ValueError("OpenAI-compatible provider requires an API key")
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds
        self._extra_headers = extra_headers or {}
        self._request_overrides = request_overrides or {}
        self._text_mode = text_mode

    def complete(self, *, system: str, user: str, model: str | None = None) -> LlmCompletion:
        use_model = model or self._model
        payload: dict[str, Any] = {
            "model": use_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0,
            **({} if self._text_mode else {"response_format": {"type": "json_object"}}),
            **self._request_overrides,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            **self._extra_headers,
        }
        with httpx.Client(timeout=self._timeout) as client:
            response = client.post(
                f"{self._base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            body = response.json()

        choice = body["choices"][0]["message"]["content"]
        usage = body.get("usage") or {}
        return LlmCompletion(
            content=choice if self._text_mode else _extract_json_content(choice),
            model=body.get("model") or use_model,
            input_tokens=int(usage.get("prompt_tokens") or 0),
            output_tokens=int(usage.get("completion_tokens") or 0),
        )


def _extract_json_content(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    json.loads(text)
    return text

"""VLM-based exception analyzer for COTA."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from openai import OpenAI

from phone_agent.model.client import MessageBuilder, ModelConfig


@dataclass
class VLMAnalyzerConfig:
    base_url: str
    api_key: str
    model_name: str
    max_tokens: int = 512
    temperature: float = 0.2
    extra_body: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_model_config(cls, model_config: ModelConfig) -> "VLMAnalyzerConfig":
        return cls(
            base_url=model_config.base_url,
            api_key=model_config.api_key,
            model_name=model_config.model_name,
            max_tokens=min(1024, model_config.max_tokens),
            temperature=max(0.1, model_config.temperature),
            extra_body=dict(model_config.extra_body or {}),
        )


@dataclass
class VLMAnalysis:
    exception_type: str
    description: str
    strategies: list[str]
    recommended_action: str
    suggested_skill: str | None
    confidence: float
    raw: str


class VLMExceptionAnalyzer:
    def __init__(self, config: VLMAnalyzerConfig) -> None:
        self.config = config
        self.client = OpenAI(base_url=config.base_url, api_key=config.api_key)

    def analyze(
        self,
        observation: Any,
        error: Any,
        recovery_skills: list[str],
    ) -> VLMAnalysis | None:
        if observation is None or not getattr(observation, "screenshot", None):
            return None
        base64_data = getattr(observation.screenshot, "base64_data", None)
        if not base64_data:
            return None

        system_prompt = (
            "You are an expert mobile UI exception analyst. "
            "Given a screenshot, error details, and recovery skill options, "
            "diagnose the issue and recommend a recovery skill. "
            "Return only JSON."
        )

        payload = {
            "error_code": getattr(getattr(error, "code", None), "value", None),
            "error_message": getattr(error, "message", ""),
            "stage": getattr(error, "stage", None),
            "step_id": getattr(error, "step_id", None),
            "attempt": getattr(error, "attempt", None),
        }

        user_prompt = (
            "Analyze the current UI state and error context.\n"
            f"Error: {json.dumps(payload, ensure_ascii=False)}\n"
            f"Recovery skill options: {json.dumps(recovery_skills, ensure_ascii=False)}\n\n"
            "Return JSON with fields: "
            "exception_type, description, strategies (array), recommended_action, "
            "suggested_skill, confidence (0-1)."
        )

        messages = [
            MessageBuilder.create_system_message(system_prompt),
            MessageBuilder.create_user_message(user_prompt, image_base64=base64_data),
        ]

        response = self.client.chat.completions.create(
            messages=messages,
            model=self.config.model_name,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            extra_body=self.config.extra_body,
        )

        content = ""
        if response and response.choices:
            message = response.choices[0].message
            if isinstance(message.content, list):
                content = "".join(
                    item.get("text", "") for item in message.content if isinstance(item, dict)
                )
            else:
                content = message.content or ""

        data = _extract_json(content)
        if not data:
            return None

        return VLMAnalysis(
            exception_type=str(data.get("exception_type", "unknown")),
            description=str(data.get("description", "")),
            strategies=list(data.get("strategies", []) or []),
            recommended_action=str(data.get("recommended_action", "")),
            suggested_skill=data.get("suggested_skill"),
            confidence=_to_float(data.get("confidence")),
            raw=content,
        )


def _extract_json(text: str) -> dict[str, Any] | None:
    if not text:
        return None
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    fenced = re.search(r"```json\s*(\{.*?\})\s*```", text, flags=re.S)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except json.JSONDecodeError:
            return None

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    snippet = text[start : end + 1]
    try:
        return json.loads(snippet)
    except json.JSONDecodeError:
        return None


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0

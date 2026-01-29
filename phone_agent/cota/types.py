"""Types for the COTA coordination layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PlanStepKind(str, Enum):
    SKILL = "skill"
    INTENT = "intent"
    LLM = "llm"
    WAIT = "wait"


@dataclass
class Intent:
    name: str
    params: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    source: str = "system2"


@dataclass
class PlanStep:
    step_id: str
    kind: PlanStepKind
    skill_id: str | None = None
    inputs: dict[str, Any] = field(default_factory=dict)
    intent: Intent | None = None
    description: str | None = None
    timeout_s: float | None = None


@dataclass
class Plan:
    task: str
    steps: list[PlanStep]
    reason: str = ""
    blocked: bool = False
    blocked_reason: str = ""


@dataclass
class ExceptionContext:
    message: str
    error_code: str | None = None
    step_id: str | None = None
    attempt: int | None = None
    details: dict[str, Any] = field(default_factory=dict)

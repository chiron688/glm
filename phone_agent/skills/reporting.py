"""Reporting data structures for skill runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from phone_agent.skills.errors import SkillError


@dataclass
class StepAttemptReport:
    attempt: int
    action: dict[str, Any] | None
    success: bool
    error: SkillError | None
    started_at: float
    ended_at: float


@dataclass
class StepReport:
    step_id: str
    attempts: list[StepAttemptReport] = field(default_factory=list)
    success: bool = False


@dataclass
class SkillRunReport:
    skill_id: str
    started_at: float
    ended_at: float
    inputs: dict[str, Any]
    steps: list[StepReport] = field(default_factory=list)


@dataclass
class SkillRunResult:
    success: bool
    message: str
    error: SkillError | None
    report: SkillRunReport

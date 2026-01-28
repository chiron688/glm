"""Skill error types and codes."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class SkillErrorCode(str, Enum):
    PRECONDITION_FAILED = "PRECONDITION_FAILED"
    PRECONDITION_UNKNOWN = "PRECONDITION_UNKNOWN"
    SCREEN_MISMATCH = "SCREEN_MISMATCH"
    TARGET_NOT_FOUND = "TARGET_NOT_FOUND"
    ACTION_FAILED = "ACTION_FAILED"
    ACTION_EXCEPTION = "ACTION_EXCEPTION"
    POSTCONDITION_FAILED = "POSTCONDITION_FAILED"
    TIMEOUT = "TIMEOUT"
    DEVICE_ERROR = "DEVICE_ERROR"
    ERROR_SCREEN_DETECTED = "ERROR_SCREEN_DETECTED"
    HANDLER_FAILED = "HANDLER_FAILED"
    ABORTED = "ABORTED"
    UNKNOWN = "UNKNOWN"


@dataclass
class SkillError:
    code: SkillErrorCode
    message: str
    stage: str
    step_id: str | None = None
    error_id: str | None = None
    attempt: int | None = None
    details: dict[str, Any] | None = None
    requires_takeover: bool = False
    exception: Exception | None = None

    def with_details(self, **kwargs: Any) -> "SkillError":
        merged = dict(self.details or {})
        merged.update(kwargs)
        return SkillError(
            code=self.code,
            message=self.message,
            stage=self.stage,
            step_id=self.step_id,
            error_id=self.error_id,
            attempt=self.attempt,
            details=merged,
            requires_takeover=self.requires_takeover,
            exception=self.exception,
        )

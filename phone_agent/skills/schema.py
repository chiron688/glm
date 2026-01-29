"""Skill schema validation and normalization."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class SkillSchemaError(ValueError):
    def __init__(self, message: str, errors: list[str] | None = None) -> None:
        """初始化技能结构校验错误，并保存错误明细。"""
        # 关键步骤：保存错误详情并初始化异常（技能结构）
        super().__init__(message)
        self.errors = errors or []


@dataclass
class SkillDefinition:
    skill_id: str
    name: str
    version: str
    source: str
    spec: dict[str, Any]


def _normalize_steps(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """用于技能结构，归一化步骤。"""
    # 关键步骤：归一化步骤（技能结构）
    normalized: list[dict[str, Any]] = []
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            continue
        step_copy = dict(step)
        if not step_copy.get("id"):
            step_copy["id"] = f"step_{index + 1}"
        normalized.append(step_copy)
    return normalized


def validate_skill_spec(spec: dict[str, Any], source: str) -> dict[str, Any]:
    """校验并规范化技能 spec，返回标准化结构。"""
    # 关键步骤：校验字段并补齐默认值（技能结构）
    errors: list[str] = []
    if not isinstance(spec, dict):
        raise SkillSchemaError("Skill spec must be a mapping", [source])

    for key in ("id", "name", "version"):
        if not spec.get(key):
            errors.append(f"Missing required field: {key}")

    steps = spec.get("steps")
    if not isinstance(steps, list) or not steps:
        errors.append("Field 'steps' must be a non-empty list")
    else:
        for index, step in enumerate(steps):
            if not isinstance(step, dict):
                errors.append(f"Step {index} must be a mapping")
                continue
            if not step.get("action"):
                errors.append(f"Step {index} missing action")

    if errors:
        raise SkillSchemaError(f"Skill schema invalid: {source}", errors)

    normalized = dict(spec)
    normalized.setdefault("schema_version", "v1")
    normalized["steps"] = _normalize_steps(steps or [])
    return normalized

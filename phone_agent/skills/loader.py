"""Skill YAML loader."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from phone_agent.skills.schema import SkillDefinition, SkillSchemaError, validate_skill_spec


def _load_yaml(path: Path) -> dict[str, Any]:
    """读取并解析 YAML 技能文件为字典结构。"""
    # 关键步骤：解析 YAML 文件（技能加载）
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
            if data is None:
                raise SkillSchemaError("Empty skill file", [str(path)])
            if not isinstance(data, dict):
                raise SkillSchemaError("Top-level YAML must be a mapping", [str(path)])
            return data
    except yaml.YAMLError as exc:
        raise SkillSchemaError(f"Failed to parse YAML: {path}") from exc


def load_skill_file(path: str | Path) -> SkillDefinition:
    """从 YAML 文件加载并校验技能定义。"""
    # 关键步骤：解析与校验技能文件（技能加载）
    path_obj = Path(path)
    spec = _load_yaml(path_obj)
    normalized = validate_skill_spec(spec, str(path_obj))
    return SkillDefinition(
        skill_id=normalized["id"],
        name=normalized["name"],
        version=normalized["version"],
        source=str(path_obj),
        spec=normalized,
    )


def load_skill_from_json(text: str, source: str = "<json>") -> SkillDefinition:
    """从 JSON 字符串加载并校验技能定义。"""
    # 关键步骤：解析 JSON 并校验（技能加载）
    try:
        spec = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SkillSchemaError(f"Invalid JSON: {source}") from exc
    normalized = validate_skill_spec(spec, source)
    return SkillDefinition(
        skill_id=normalized["id"],
        name=normalized["name"],
        version=normalized["version"],
        source=source,
        spec=normalized,
    )

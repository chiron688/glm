"""Skill registry for loading and lookups."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from phone_agent.skills.loader import load_skill_file
from phone_agent.skills.schema import SkillDefinition, SkillSchemaError


@dataclass
class SkillRegistry:
    skills: dict[str, SkillDefinition] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def register(self, skill: SkillDefinition) -> None:
        """注册技能定义到注册表，并按 skill_id 建立索引。"""
        # 关键步骤：写入技能索引（技能注册）
        self.skills[skill.skill_id] = skill

    def get(self, skill_id: str) -> SkillDefinition | None:
        """按 skill_id 查询技能定义。"""
        # 关键步骤：按 ID 返回技能定义（技能注册）
        return self.skills.get(skill_id)

    def list(self) -> list[SkillDefinition]:
        """返回全部已注册的技能定义列表。"""
        # 关键步骤：汇总技能定义列表（技能注册）
        return list(self.skills.values())

    def list_by_level(self, level: int) -> list[SkillDefinition]:
        """按 level 过滤技能定义列表。"""
        # 关键步骤：按等级筛选技能（技能注册）
        return [skill for skill in self.skills.values() if skill.spec.get("level") == level]

    def list_by_role(self, role: str) -> list[SkillDefinition]:
        """按 role 过滤技能定义列表。"""
        # 关键步骤：按角色筛选技能（技能注册）
        return [skill for skill in self.skills.values() if skill.spec.get("role") == role]

    def list_by_owner(self, owner: str) -> list[SkillDefinition]:
        """按 owner 过滤技能定义列表。"""
        # 关键步骤：按归属筛选技能（技能注册）
        return [skill for skill in self.skills.values() if skill.spec.get("owner") == owner]

    def load_from_paths(self, paths: Iterable[str | Path]) -> None:
        """从路径列表加载技能定义（支持目录递归）。"""
        # 关键步骤：遍历路径加载技能（技能注册）
        for path in paths:
            self._load_path(Path(path))

    def _load_path(self, path: Path) -> None:
        """处理单个路径，目录则递归加载 YAML 技能文件。"""
        # 关键步骤：识别目录或文件并加载（技能注册）
        if path.is_dir():
            for file_path in path.rglob("*.yml"):
                self._load_file(file_path)
            for file_path in path.rglob("*.yaml"):
                self._load_file(file_path)
        elif path.is_file():
            self._load_file(path)

    def _load_file(self, path: Path) -> None:
        """解析单个 YAML 文件并注册，失败时记录错误。"""
        # 关键步骤：解析并注册技能文件（技能注册）
        try:
            skill = load_skill_file(path)
            self.register(skill)
        except SkillSchemaError as exc:
            message = f"{path}: {exc}"
            self.errors.append(message)

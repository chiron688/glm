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
        self.skills[skill.skill_id] = skill

    def get(self, skill_id: str) -> SkillDefinition | None:
        return self.skills.get(skill_id)

    def list(self) -> list[SkillDefinition]:
        return list(self.skills.values())

    def list_by_level(self, level: int) -> list[SkillDefinition]:
        return [skill for skill in self.skills.values() if skill.spec.get("level") == level]

    def list_by_role(self, role: str) -> list[SkillDefinition]:
        return [skill for skill in self.skills.values() if skill.spec.get("role") == role]

    def list_by_owner(self, owner: str) -> list[SkillDefinition]:
        return [skill for skill in self.skills.values() if skill.spec.get("owner") == owner]

    def load_from_paths(self, paths: Iterable[str | Path]) -> None:
        for path in paths:
            self._load_path(Path(path))

    def _load_path(self, path: Path) -> None:
        if path.is_dir():
            for file_path in path.rglob("*.yml"):
                self._load_file(file_path)
            for file_path in path.rglob("*.yaml"):
                self._load_file(file_path)
        elif path.is_file():
            self._load_file(path)

    def _load_file(self, path: Path) -> None:
        try:
            skill = load_skill_file(path)
            self.register(skill)
        except SkillSchemaError as exc:
            message = f"{path}: {exc}"
            self.errors.append(message)

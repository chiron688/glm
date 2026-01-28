"""Skill router for task-to-skill selection."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

import yaml

from phone_agent.skills.conditions import evaluate_condition
from phone_agent.skills.registry import SkillRegistry
from phone_agent.skills.utils import render_templates


@dataclass(frozen=True)
class SkillDirective:
    skill_id: str
    inputs: dict[str, Any]
    reason: str


@dataclass
class SkillRouterConfig:
    enabled: bool = True
    risk_first: bool = True
    min_score: int = 1
    allow_directive: bool = True
    enforce_skill_whitelist: bool = False
    skill_whitelist: list[str] = field(default_factory=list)
    enforce_on_risk: bool = False
    risk_keywords: list[str] = field(default_factory=list)
    default_vocab_path: str | None = "skills/common/vocab.yaml"


@dataclass(frozen=True)
class RoutingDecision:
    action: str
    directive: SkillDirective | None = None
    reason: str = ""


class SkillRouter:
    def __init__(self, registry: SkillRegistry, config: SkillRouterConfig | None = None) -> None:
        self.registry = registry
        self.config = config or SkillRouterConfig()

    def select(
        self, task: str, observation: Any | None = None
    ) -> RoutingDecision:
        if not self.config.enabled:
            return RoutingDecision(action="none")
        directive = self._parse_directive(task) if self.config.allow_directive else None
        if directive:
            if self._is_blocked(directive.skill_id, task):
                return RoutingDecision(action="block", reason="whitelist-block")
            if self.registry.get(directive.skill_id):
                return RoutingDecision(action="skill", directive=directive, reason=directive.reason)
            return RoutingDecision(action="none")

        candidates: list[tuple[float, SkillDirective]] = []
        for skill in self.registry.list():
            score, reason = self._score_skill(skill.spec, task, observation)
            if score >= self.config.min_score:
                candidates.append(
                    (
                        score,
                        SkillDirective(
                            skill_id=skill.skill_id,
                            inputs={},
                            reason=reason or "routing-match",
                        ),
                    )
                )

        if not candidates:
            if self._risk_block(task):
                return RoutingDecision(action="block", reason="risk-requires-skill")
            return RoutingDecision(action="none")
        candidates.sort(key=lambda item: item[0], reverse=True)
        decision = candidates[0][1]
        if self._is_blocked(decision.skill_id, task):
            return RoutingDecision(action="block", reason="whitelist-block")
        return RoutingDecision(action="skill", directive=decision, reason=decision.reason)

    def _parse_directive(self, task: str) -> SkillDirective | None:
        text = task.strip()
        if text.startswith("{") and text.endswith("}"):
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                payload = None
            if isinstance(payload, dict) and ("skill_id" in payload or "skill" in payload):
                skill_id = payload.get("skill_id") or payload.get("skill")
                inputs = payload.get("inputs") if isinstance(payload.get("inputs"), dict) else {}
                return SkillDirective(skill_id=skill_id, inputs=inputs, reason="json-directive")

        match = re.search(r"(?:^|\s)skill:([^\s\]|\|]+)", task)
        if match:
            skill_id = match.group(1).strip()
            inputs: dict[str, Any] = {}
            if "|" in task:
                _, raw_inputs = task.split("|", 1)
                raw_inputs = raw_inputs.strip()
                try:
                    parsed = json.loads(raw_inputs)
                    if isinstance(parsed, dict):
                        inputs = parsed
                except json.JSONDecodeError:
                    inputs = {}
            return SkillDirective(skill_id=skill_id, inputs=inputs, reason="inline-directive")
        return None

    def _score_skill(self, spec: dict[str, Any], task: str, observation: Any | None) -> tuple[float, str]:
        routing = spec.get("routing", {}) if isinstance(spec.get("routing"), dict) else {}
        score = float(routing.get("priority", 0))
        reason = ""

        # Keyword match
        keywords = self._expand_routing_list(routing.get("keywords"), spec)
        if isinstance(keywords, list) and keywords:
            lowered = task.casefold()
            hits = sum(1 for keyword in keywords if keyword and keyword.casefold() in lowered)
            keyword_mode = routing.get("keyword_mode", "any")
            if keyword_mode == "all" and hits < len(keywords):
                return 0.0, "keyword-miss"
            if hits == 0:
                return 0.0, "keyword-miss"
            score += hits * 10
            reason = "keyword"

        # Regex match
        regex_list = self._expand_routing_list(routing.get("task_regex"), spec)
        if isinstance(regex_list, list) and regex_list:
            matched = False
            for pattern in regex_list:
                try:
                    if re.search(pattern, task, flags=re.IGNORECASE):
                        matched = True
                        score += 8
                        reason = "regex"
                        break
                except re.error:
                    continue
            if not matched:
                return 0.0, "regex-miss"

        # Require app
        require_app = routing.get("require_app")
        if require_app and observation is not None:
            if isinstance(require_app, list):
                if observation.app_name not in require_app:
                    return 0.0, "app-miss"
                score += 5
            elif isinstance(require_app, str):
                if observation.app_name != require_app:
                    return 0.0, "app-miss"
                score += 5

        # Optional preconditions
        preconditions = routing.get("preconditions")
        if preconditions and observation is not None:
            result = evaluate_condition(preconditions, observation)
            if result is False:
                return 0.0, "precondition-miss"
            if result is True:
                score += 4

        # Risk boost
        if self.config.risk_first:
            risk = spec.get("risk")
            if risk == "high":
                score += 6
            elif risk == "medium":
                score += 3

        return score, reason or "routing"

    def _expand_routing_list(self, values: Any, spec: dict[str, Any]) -> list[str] | Any:
        if not isinstance(values, list):
            return values
        vocab = self._load_vocab(spec)
        if not vocab:
            return values
        rendered = render_templates(values, vocab)
        flattened: list[str] = []
        for item in rendered:
            if isinstance(item, list):
                for sub in item:
                    if isinstance(sub, str) and sub.strip():
                        flattened.append(sub)
            elif isinstance(item, str) and item.strip():
                flattened.append(item)
        return flattened

    def _load_vocab(self, spec: dict[str, Any]) -> dict[str, Any]:
        vocab: dict[str, Any] = {}
        inline = spec.get("vocab")
        if isinstance(inline, dict):
            vocab.update(inline)
        path = spec.get("vocab_path") or self.config.default_vocab_path
        if not path:
            return vocab
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = yaml.safe_load(handle)
            if isinstance(data, dict):
                vocab.update(data)
        except Exception:
            return vocab
        return vocab

    def _risk_block(self, task: str) -> bool:
        if not self.config.enforce_on_risk:
            return False
        keywords = self.config.risk_keywords or []
        lowered = task.casefold()
        return any(keyword.casefold() in lowered for keyword in keywords if keyword)

    def _is_blocked(self, skill_id: str, task: str) -> bool:
        if self.config.enforce_skill_whitelist:
            if skill_id not in self.config.skill_whitelist:
                return True
        if self._risk_block(task) and skill_id not in self.config.skill_whitelist:
            return True
        return False

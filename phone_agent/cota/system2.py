"""Slow planning system (System 2) for COTA."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from phone_agent.skills.errors import SkillError
from phone_agent.skills.registry import SkillRegistry
from phone_agent.skills.router import SkillRouter

from phone_agent.cota.config import COTAConfig
from phone_agent.cota.vlm_analyzer import VLMAnalysis, VLMExceptionAnalyzer
from phone_agent.cota.types import ExceptionContext, Plan, PlanStep, PlanStepKind


@dataclass
class RecoveryDecision:
    action: str
    step: PlanStep | None = None
    reason: str = ""


class SlowPlannerSystem:
    def __init__(
        self,
        config: COTAConfig,
        skill_registry: SkillRegistry | None = None,
        skill_router: SkillRouter | None = None,
        llm_agent: Any | None = None,
        vlm_analyzer: VLMExceptionAnalyzer | None = None,
    ) -> None:
        self.config = config
        self.skill_registry = skill_registry
        self.skill_router = skill_router
        self.llm_agent = llm_agent
        self.vlm_analyzer = vlm_analyzer

    def plan(self, task: str, observation: Any | None) -> Plan:
        if (
            self.config.system2.enable_skill_routing
            and self.skill_router is not None
            and self.skill_registry is not None
        ):
            decision = self.skill_router.select(task, observation)
            if decision.action == "block":
                return Plan(
                    task=task,
                    steps=[],
                    reason="blocked",
                    blocked=True,
                    blocked_reason=decision.reason,
                )
            if decision.action == "skill" and decision.directive:
                return Plan(
                    task=task,
                    steps=[
                        PlanStep(
                            step_id="skill_1",
                            kind=PlanStepKind.SKILL,
                            skill_id=decision.directive.skill_id,
                            inputs=decision.directive.inputs,
                            description=decision.directive.reason,
                        )
                    ],
                    reason=decision.reason,
                )

        return Plan(
            task=task,
            steps=[
                PlanStep(
                    step_id="llm_fallback",
                    kind=PlanStepKind.LLM,
                    description="llm_fallback",
                )
            ],
            reason="llm_fallback",
        )

    def recover(self, error: SkillError, observation: Any | None) -> RecoveryDecision:
        if not self.config.system2.enable_exception_skills:
            return RecoveryDecision(action="none", reason="exception_skills_disabled")

        analysis = self._analyze_exception(error, observation)
        if analysis and analysis.suggested_skill:
            step = self._build_skill_step(analysis.suggested_skill, "vlm_recovery")
            if step:
                return RecoveryDecision(action="skill", step=step, reason="vlm_recovery")

        skill_id = self._map_error_to_skill(error)
        if skill_id and self.skill_registry and self.skill_registry.get(skill_id):
            step = PlanStep(
                step_id=f"recovery_{skill_id}",
                kind=PlanStepKind.SKILL,
                skill_id=skill_id,
                inputs={},
                description="exception_recovery",
            )
            return RecoveryDecision(action="skill", step=step, reason="mapped_exception")

        return RecoveryDecision(action="llm", reason="fallback_to_llm")

    def execute_llm(self, task: str) -> str:
        if self.llm_agent is None:
            return "LLM agent not configured"
        return self.llm_agent.run(task)

    def _map_error_to_skill(self, error: SkillError) -> str | None:
        code = error.code.value if error and error.code else ""
        return self.config.exception_skill_map.get(code)

    def _analyze_exception(self, error: SkillError, observation: Any | None) -> VLMAnalysis | None:
        if not self.config.system2.enable_vlm_recovery or self.vlm_analyzer is None:
            return None
        if observation is None:
            return None
        recovery_skills = self._list_recovery_skills()
        if not recovery_skills:
            return None
        try:
            analysis = self.vlm_analyzer.analyze(observation, error, recovery_skills)
        except Exception:
            return None
        if not analysis:
            return None
        threshold = self.config.system2.vlm_confidence_threshold
        if analysis.confidence < threshold:
            return None
        if analysis.suggested_skill and analysis.suggested_skill in recovery_skills:
            return analysis
        return None

    def _list_recovery_skills(self) -> list[str]:
        if not self.skill_registry:
            return []
        recovery = []
        for skill in self.skill_registry.list():
            if skill.spec.get("level") == 3 or skill.spec.get("role") == "recovery":
                recovery.append(skill.skill_id)
        return recovery

    def _build_skill_step(self, skill_id: str, reason: str) -> PlanStep | None:
        if not self.skill_registry or not self.skill_registry.get(skill_id):
            return None
        return PlanStep(
            step_id=f"recovery_{skill_id}",
            kind=PlanStepKind.SKILL,
            skill_id=skill_id,
            inputs={},
            description=reason,
        )

    def build_exception_context(self, error: SkillError) -> ExceptionContext:
        return ExceptionContext(
            message=error.message,
            error_code=error.code.value if error.code else None,
            step_id=error.step_id,
            attempt=error.attempt,
            details=error.to_dict() if hasattr(error, "to_dict") else {},
        )

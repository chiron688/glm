"""Slow planning system (System 2) for COTA."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from phone_agent.skills.errors import SkillError
from phone_agent.skills.learning import SkillLearningRecorder
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
        learning_recorder: SkillLearningRecorder | None = None,
    ) -> None:
        """初始化 System2 规划器，注入路由、技能与 VLM 分析能力。"""
        # 关键步骤：准备规划依赖（System2 规划）
        self.config = config
        self.skill_registry = skill_registry
        self.skill_router = skill_router
        self.llm_agent = llm_agent
        self.vlm_analyzer = vlm_analyzer
        self.learning_recorder = learning_recorder

    def plan(self, task: str, observation: Any | None) -> Plan:
        """根据任务与观察生成计划步骤（优先 Skills）。"""
        # 关键步骤：生成任务计划（System2 规划）
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
            if decision.action == "shadow" and decision.directive:
                if self.learning_recorder:
                    self.learning_recorder.record_shadow_match(
                        task=task,
                        observation=observation,
                        skill_id=decision.directive.skill_id,
                        reason=decision.reason or "shadow-match",
                    )
                return Plan(
                    task=task,
                    steps=[],
                    reason="shadow",
                    blocked=True,
                    blocked_reason="shadow-match",
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

        if self.learning_recorder:
            self.learning_recorder.record_case(
                task=task,
                reason="no_skill_match",
                observation=observation,
                extra={"route_reason": "no_skill_match"},
            )
        return Plan(
            task=task,
            steps=[],
            reason="no_skill_match",
            blocked=True,
            blocked_reason="no_skill_match",
        )

    def recover(self, error: SkillError, observation: Any | None) -> RecoveryDecision:
        """根据错误与观察选择恢复技能或放弃恢复。"""
        # 关键步骤：决策恢复路径（System2 规划）
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

        return RecoveryDecision(action="none", reason="no_recovery_skill")

    def execute_llm(self, task: str) -> str:
        """调用 LLM 进行兜底执行（可选能力）。"""
        # 关键步骤：执行 LLM 兜底（System2 规划）
        if self.llm_agent is None:
            return "LLM agent not configured"
        return self.llm_agent.run(task)

    def _map_error_to_skill(self, error: SkillError) -> str | None:
        """按错误码映射到恢复技能。"""
        # 关键步骤：错误码到技能映射
        code = error.code.value if error and error.code else ""
        return self.config.exception_skill_map.get(code)

    def _analyze_exception(self, error: SkillError, observation: Any | None) -> VLMAnalysis | None:
        """调用 VLM 分析异常截图并给出恢复建议。"""
        # 关键步骤：VLM 异常分析（System2 规划）
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
        """列出 Level 3/Recovery 级别的恢复技能。"""
        # 关键步骤：汇总恢复技能列表（System2 规划）
        if not self.skill_registry:
            return []
        recovery = []
        for skill in self.skill_registry.list():
            if skill.spec.get("level") == 3 or skill.spec.get("role") == "recovery":
                recovery.append(skill.skill_id)
        return recovery

    def _build_skill_step(self, skill_id: str, reason: str) -> PlanStep | None:
        """构建恢复技能对应的计划步骤。"""
        # 关键步骤：生成恢复步骤（System2 规划）
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
        """构建异常上下文，供 VLM 与恢复策略使用。"""
        # 关键步骤：整理异常上下文（System2 规划）
        return ExceptionContext(
            message=error.message,
            error_code=error.code.value if error.code else None,
            step_id=error.step_id,
            attempt=error.attempt,
            details=error.to_dict() if hasattr(error, "to_dict") else {},
        )

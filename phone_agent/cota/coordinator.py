"""Coordinator for COTA's dual-system execution."""

from __future__ import annotations

from typing import Any

from phone_agent.skills.observation import ObservationProvider

from phone_agent.cota.types import PlanStepKind


class COTACoordinator:
    def __init__(
        self,
        system1: Any,
        system2: Any,
        skill_runner: Any | None = None,
        observer: Any | None = None,
    ) -> None:
        """初始化协调器，注入 System1/2、技能执行与观察器。"""
        # 关键步骤：装配双系统协同依赖
        self.system1 = system1
        self.system2 = system2
        self.skill_runner = skill_runner
        self.observer = observer or (skill_runner.observer if skill_runner else ObservationProvider())

    def run(self, task: str) -> str:
        """用于双系统协同，执行计划步骤与恢复流程。"""
        # 关键步骤：执行计划步骤与恢复流程（双系统协同）
        observation = self._safe_capture()
        plan = self.system2.plan(task, observation)

        if plan.blocked:
            if plan.blocked_reason == "no_skill_match":
                return "No matching skill for task"
            return f"Blocked: {plan.blocked_reason}"

        for step in plan.steps:
            if step.kind == PlanStepKind.LLM:
                return "LLM engine is disabled"

            if step.kind == PlanStepKind.INTENT:
                result = self.system1.execute_intent(step.intent, observation)
                if result is None:
                    return "Intent execution failed"
                observation = self._safe_capture()
                self.system1.maintain_liveness(observation)
                continue

            if step.kind == PlanStepKind.SKILL:
                if self.skill_runner is None:
                    return "Skill runner not configured"
                result = self.skill_runner.run(step.skill_id, step.inputs)
                if result.success:
                    observation = self._safe_capture()
                    continue

                if result.error is None:
                    return result.message or "Task failed"

                if result.error and getattr(result.error, "requires_takeover", False):
                    return result.message or "Manual takeover required"

                recovery = self.system2.recover(result.error, observation)
                if recovery.action == "skill" and recovery.step:
                    recovery_result = self.skill_runner.run(
                        recovery.step.skill_id, recovery.step.inputs
                    )
                    if recovery_result.success:
                        retry_result = self.skill_runner.run(step.skill_id, step.inputs)
                        if retry_result.success:
                            observation = self._safe_capture()
                            continue
                        return retry_result.message or "Task failed after recovery"
                    return recovery_result.message or "Recovery failed"

                if recovery.action == "llm":
                    return "LLM engine is disabled"

                return result.message or "Task failed"

        return "Task completed"

    def _safe_capture(self):
        """安全采集观察信息，失败时返回 None。"""
        # 关键步骤：容错采集观察数据
        try:
            return self.observer.capture()
        except Exception:
            return None

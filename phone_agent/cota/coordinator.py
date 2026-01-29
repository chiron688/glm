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
        self.system1 = system1
        self.system2 = system2
        self.skill_runner = skill_runner
        self.observer = observer or (skill_runner.observer if skill_runner else ObservationProvider())

    def run(self, task: str) -> str:
        observation = self._safe_capture()
        plan = self.system2.plan(task, observation)

        if plan.blocked:
            return f"Blocked by risk gate: {plan.blocked_reason}"

        for step in plan.steps:
            if step.kind == PlanStepKind.LLM:
                return self.system2.execute_llm(task)

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
                    return self.system2.execute_llm(task)

                return result.message or "Task failed"

        return "Task completed"

    def _safe_capture(self):
        try:
            return self.observer.capture()
        except Exception:
            return None

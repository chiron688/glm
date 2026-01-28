"""Skill runner implementation."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from phone_agent.actions import ActionHandler
from phone_agent.skills.common_handlers import load_common_handlers
from phone_agent.skills.conditions import evaluate_condition
from phone_agent.skills.errors import SkillError, SkillErrorCode
from phone_agent.skills.observation import (
    Observation,
    ObservationProvider,
    PlaybackObservationProvider,
    RecordingObservationProvider,
)
from phone_agent.skills.ocr import OcrProvider
from phone_agent.skills.registry import SkillRegistry
from phone_agent.skills.reporting import (
    SkillRunReport,
    SkillRunResult,
    StepAttemptReport,
    StepReport,
)
from phone_agent.skills.selector import resolve_selector_to_point
from phone_agent.skills.utils import render_templates, sleep_with_backoff


@dataclass
class RetryPolicy:
    max_attempts: int = 1
    backoff_ms: int = 0
    backoff_multiplier: float = 1.0
    max_backoff_ms: int = 0
    jitter_ms: int = 0
    on_codes: list[str] | None = None


@dataclass
class SkillRunnerConfig:
    strict_preconditions: bool = True
    strict_postconditions: bool = True
    include_ui_tree: bool = True
    include_screen_hash: bool = True
    ocr_provider: OcrProvider | None = None
    default_retry: RetryPolicy = field(default_factory=RetryPolicy)
    max_handler_cycles: int = 3
    verbose: bool = True
    dry_run: bool = False
    common_error_handlers_path: str | None = None
    common_error_handlers: list[dict[str, Any]] | None = None
    record_dir: str | None = None
    playback_dir: str | None = None


@dataclass
class HandlerOutcome:
    resolution: str
    retry_policy: RetryPolicy | None = None
    error: SkillError | None = None


class SkillRunner:
    def __init__(
        self,
        registry: SkillRegistry,
        config: SkillRunnerConfig | None = None,
        device_id: str | None = None,
        action_handler: ActionHandler | None = None,
    ) -> None:
        self.registry = registry
        self.config = config or SkillRunnerConfig()
        self.device_id = device_id
        self.action_handler = action_handler or ActionHandler(device_id=device_id)
        self.observer = self._build_observer()

    def _build_observer(self):
        if self.config.playback_dir:
            return PlaybackObservationProvider(self.config.playback_dir)

        observer = ObservationProvider(
            device_id=self.device_id,
            include_ui_tree=self.config.include_ui_tree,
            include_screen_hash=self.config.include_screen_hash,
            ocr_provider=self.config.ocr_provider,
        )
        if self.config.record_dir:
            return RecordingObservationProvider(observer, self.config.record_dir)
        return observer

    def run(self, skill_id: str, inputs: dict[str, Any] | None = None) -> SkillRunResult:
        skill = self.registry.get(skill_id)
        if not skill:
            error = SkillError(
                code=SkillErrorCode.UNKNOWN,
                message=f"Skill not found: {skill_id}",
                stage="load",
            )
            report = SkillRunReport(
                skill_id=skill_id,
                started_at=time.time(),
                ended_at=time.time(),
                inputs=inputs or {},
            )
            return SkillRunResult(False, error.message, error, report)

        try:
            variables = self._prepare_variables(skill.spec, inputs or {})
        except Exception as exc:
            error = SkillError(
                code=SkillErrorCode.PRECONDITION_FAILED,
                message=str(exc),
                stage="inputs",
            )
            report = SkillRunReport(
                skill_id=skill_id,
                started_at=time.time(),
                ended_at=time.time(),
                inputs=inputs or {},
            )
            return SkillRunResult(False, error.message, error, report)
        spec = render_templates(skill.spec, variables)
        common_handlers = self._load_common_handlers(variables)
        if common_handlers:
            merged = list(common_handlers)
            merged.extend(spec.get("error_handlers", []))
            spec = dict(spec)
            spec["error_handlers"] = merged
        report = SkillRunReport(
            skill_id=skill_id,
            started_at=time.time(),
            ended_at=0.0,
            inputs=variables,
        )

        observation = self.observer.capture()

        pre_ok, observation = self._check_condition_block(
            spec.get("preconditions"),
            observation,
            stage="preconditions",
            strict=self.config.strict_preconditions,
        )
        if not pre_ok:
            error = SkillError(
                code=SkillErrorCode.PRECONDITION_FAILED
                if pre_ok is False
                else SkillErrorCode.PRECONDITION_UNKNOWN,
                message="Preconditions not satisfied",
                stage="preconditions",
            )
            outcome = self._handle_error(
                error=error,
                step=None,
                spec=spec,
                observation=observation,
            )
            report.ended_at = time.time()
            return SkillRunResult(
                success=False,
                message=outcome.error.message if outcome.error else error.message,
                error=outcome.error or error,
                report=report,
            )

        steps = spec.get("steps", [])
        for step in steps:
            step_report = StepReport(step_id=step.get("id", "unknown"))
            report.steps.append(step_report)
            success, observation, error = self._run_step(step, spec, observation, step_report)
            step_report.success = success
            if not success:
                report.ended_at = time.time()
                return SkillRunResult(
                    success=False,
                    message=error.message if error else "Step failed",
                    error=error,
                    report=report,
                )

        post_ok, observation = self._check_condition_block(
            spec.get("postconditions"),
            observation,
            stage="postconditions",
            strict=self.config.strict_postconditions,
        )
        if not post_ok:
            error = SkillError(
                code=SkillErrorCode.POSTCONDITION_FAILED,
                message="Postconditions not satisfied",
                stage="postconditions",
            )
            outcome = self._handle_error(
                error=error,
                step=None,
                spec=spec,
                observation=observation,
            )
            report.ended_at = time.time()
            return SkillRunResult(
                success=False,
                message=outcome.error.message if outcome.error else error.message,
                error=outcome.error or error,
                report=report,
            )

        report.ended_at = time.time()
        return SkillRunResult(True, "Skill completed", None, report)

    def _prepare_variables(self, spec: dict[str, Any], inputs: dict[str, Any]) -> dict[str, Any]:
        variables = dict(spec.get("vars", {}))
        input_specs = spec.get("inputs", {})
        if isinstance(input_specs, dict):
            for name, meta in input_specs.items():
                if isinstance(meta, dict) and "default" in meta and name not in inputs:
                    variables[name] = meta.get("default")
                elif name in inputs:
                    variables[name] = inputs[name]
                elif isinstance(meta, dict) and meta.get("required"):
                    raise ValueError(f"Missing required input: {name}")
        elif isinstance(input_specs, list):
            for entry in input_specs:
                if isinstance(entry, dict):
                    name = entry.get("name")
                    if not name:
                        continue
                    if name in inputs:
                        variables[name] = inputs[name]
                    elif "default" in entry:
                        variables[name] = entry.get("default")
                    elif entry.get("required"):
                        raise ValueError(f"Missing required input: {name}")
        variables.update(inputs)
        variables.setdefault("timestamp", int(time.time()))
        # Resolve nested templates inside variables (e.g. defaults referencing vars).
        variables = render_templates(variables, variables)
        return variables

    def _load_common_handlers(self, variables: dict[str, Any]) -> list[dict[str, Any]]:
        handlers: list[dict[str, Any]] = []
        if self.config.common_error_handlers_path:
            handlers.extend(load_common_handlers(self.config.common_error_handlers_path))
        if self.config.common_error_handlers:
            handlers.extend(self.config.common_error_handlers)
        if not handlers:
            return []
        return render_templates(handlers, variables)

    def _run_step(
        self,
        step: dict[str, Any],
        spec: dict[str, Any],
        observation: Observation,
        step_report: StepReport,
    ) -> tuple[bool, Observation, SkillError | None]:
        retry_policy = self._parse_retry_policy(step.get("retry"), self.config.default_retry)
        max_attempts = max(1, retry_policy.max_attempts)

        attempt = 0
        while attempt < max_attempts:
            attempt += 1
            attempt_start = time.time()

            observation = self.observer.capture()
            observation = self._apply_before_step_handlers(step, spec, observation)

            guard_ok, observation = self._check_condition_block(
                step.get("guard"),
                observation,
                stage="guard",
                strict=self.config.strict_preconditions,
            )
            if guard_ok is False:
                error = SkillError(
                    code=SkillErrorCode.SCREEN_MISMATCH,
                    message="Step guard failed",
                    stage="guard",
                    step_id=step.get("id"),
                    attempt=attempt,
                )
                outcome = self._handle_error(error, step, spec, observation)
                step_report.attempts.append(
                    StepAttemptReport(
                        attempt=attempt,
                        action=None,
                        success=False,
                        error=outcome.error or error,
                        started_at=attempt_start,
                        ended_at=time.time(),
                    )
                )
                if outcome.resolution == "continue":
                    return True, observation, None
                if outcome.resolution == "abort":
                    return False, observation, outcome.error or error
                if outcome.resolution == "escalate":
                    return False, observation, outcome.error or error
                policy = outcome.retry_policy or retry_policy
                if not self._should_retry(error, policy, attempt):
                    return False, observation, outcome.error or error
                self._backoff(attempt, policy)
                continue
            if guard_ok is None and self.config.strict_preconditions:
                error = SkillError(
                    code=SkillErrorCode.PRECONDITION_UNKNOWN,
                    message="Step guard unknown",
                    stage="guard",
                    step_id=step.get("id"),
                    attempt=attempt,
                )
                outcome = self._handle_error(error, step, spec, observation)
                step_report.attempts.append(
                    StepAttemptReport(
                        attempt=attempt,
                        action=None,
                        success=False,
                        error=outcome.error or error,
                        started_at=attempt_start,
                        ended_at=time.time(),
                    )
                )
                if outcome.resolution in ("continue", "abort", "escalate"):
                    return outcome.resolution == "continue", observation, outcome.error
                policy = outcome.retry_policy or retry_policy
                if not self._should_retry(error, policy, attempt):
                    return False, observation, outcome.error or error
                self._backoff(attempt, policy)
                continue

            wait_before_ms = step.get("wait", {}).get("before_ms") if isinstance(step.get("wait"), dict) else None
            if isinstance(wait_before_ms, int) and wait_before_ms > 0:
                time.sleep(wait_before_ms / 1000.0)

            try:
                action = self._build_action(step, observation)
            except SkillError as exc:
                error = exc
                outcome = self._handle_error(error, step, spec, observation)
                step_report.attempts.append(
                    StepAttemptReport(
                        attempt=attempt,
                        action=None,
                        success=False,
                        error=outcome.error or error,
                        started_at=attempt_start,
                        ended_at=time.time(),
                    )
                )
                if outcome.resolution == "continue":
                    return True, observation, None
                if outcome.resolution in ("abort", "escalate"):
                    return False, observation, outcome.error or error
                policy = outcome.retry_policy or retry_policy
                if not self._should_retry(error, policy, attempt):
                    return False, observation, outcome.error or error
                self._backoff(attempt, policy)
                continue

            if self.config.dry_run:
                action_result = True
            else:
                try:
                    result = self.action_handler.execute(action, observation.width, observation.height)
                    action_result = result.success
                except Exception as exc:
                    error = SkillError(
                        code=SkillErrorCode.ACTION_EXCEPTION,
                        message=str(exc),
                        stage="action",
                        step_id=step.get("id"),
                        attempt=attempt,
                        exception=exc,
                    )
                    outcome = self._handle_error(error, step, spec, observation)
                    step_report.attempts.append(
                        StepAttemptReport(
                            attempt=attempt,
                            action=action,
                            success=False,
                            error=outcome.error or error,
                            started_at=attempt_start,
                            ended_at=time.time(),
                        )
                    )
                if outcome.resolution == "continue":
                    return True, observation, None
                if outcome.resolution in ("abort", "escalate"):
                    return False, observation, outcome.error or error
                policy = outcome.retry_policy or retry_policy
                if not self._should_retry(error, policy, attempt):
                    return False, observation, outcome.error or error
                self._backoff(attempt, policy)
                continue

            if not action_result:
                error = SkillError(
                    code=SkillErrorCode.ACTION_FAILED,
                    message="Action failed",
                    stage="action",
                    step_id=step.get("id"),
                    attempt=attempt,
                )
                outcome = self._handle_error(error, step, spec, observation)
                step_report.attempts.append(
                    StepAttemptReport(
                        attempt=attempt,
                        action=action,
                        success=False,
                        error=outcome.error or error,
                        started_at=attempt_start,
                        ended_at=time.time(),
                    )
                )
                if outcome.resolution == "continue":
                    return True, observation, None
                if outcome.resolution in ("abort", "escalate"):
                    return False, observation, outcome.error or error
                policy = outcome.retry_policy or retry_policy
                if not self._should_retry(error, policy, attempt):
                    return False, observation, outcome.error or error
                self._backoff(attempt, policy)
                continue

            wait_after_ms = step.get("wait", {}).get("after_ms") if isinstance(step.get("wait"), dict) else None
            if isinstance(wait_after_ms, int) and wait_after_ms > 0:
                time.sleep(wait_after_ms / 1000.0)

            observation = self.observer.capture()
            assert_ok, observation = self._check_condition_block(
                step.get("assert"),
                observation,
                stage="assert",
                strict=self.config.strict_postconditions,
            )
            if assert_ok is False:
                error = SkillError(
                    code=SkillErrorCode.POSTCONDITION_FAILED,
                    message="Step assertion failed",
                    stage="assert",
                    step_id=step.get("id"),
                    attempt=attempt,
                )
                outcome = self._handle_error(error, step, spec, observation)
                step_report.attempts.append(
                    StepAttemptReport(
                        attempt=attempt,
                        action=action,
                        success=False,
                        error=outcome.error or error,
                        started_at=attempt_start,
                        ended_at=time.time(),
                    )
                )
                if outcome.resolution == "continue":
                    return True, observation, None
                if outcome.resolution in ("abort", "escalate"):
                    return False, observation, outcome.error or error
                policy = outcome.retry_policy or retry_policy
                if not self._should_retry(error, policy, attempt):
                    return False, observation, outcome.error or error
                self._backoff(attempt, policy)
                continue
            if assert_ok is None and self.config.strict_postconditions:
                error = SkillError(
                    code=SkillErrorCode.POSTCONDITION_FAILED,
                    message="Step assertion unknown",
                    stage="assert",
                    step_id=step.get("id"),
                    attempt=attempt,
                )
                outcome = self._handle_error(error, step, spec, observation)
                step_report.attempts.append(
                    StepAttemptReport(
                        attempt=attempt,
                        action=action,
                        success=False,
                        error=outcome.error or error,
                        started_at=attempt_start,
                        ended_at=time.time(),
                    )
                )
                if outcome.resolution == "continue":
                    return True, observation, None
                if outcome.resolution in ("abort", "escalate"):
                    return False, observation, outcome.error or error
                policy = outcome.retry_policy or retry_policy
                if not self._should_retry(error, policy, attempt):
                    return False, observation, outcome.error or error
                self._backoff(attempt, policy)
                continue

            step_report.attempts.append(
                StepAttemptReport(
                    attempt=attempt,
                    action=action,
                    success=True,
                    error=None,
                    started_at=attempt_start,
                    ended_at=time.time(),
                )
            )
            return True, observation, None

        return False, observation, SkillError(
            code=SkillErrorCode.ABORTED,
            message="Step retries exhausted",
            stage="retry",
            step_id=step.get("id"),
        )

    def _apply_before_step_handlers(
        self, step: dict[str, Any], spec: dict[str, Any], observation: Observation
    ) -> Observation:
        handlers = self._collect_handlers(step, spec, trigger="before_step")
        if not handlers:
            return observation
        cycles = 0
        while cycles < self.config.max_handler_cycles:
            cycles += 1
            matched = False
            for handler in handlers:
                if not self._handler_condition_matches(handler, observation):
                    continue
                matched = True
                self._execute_handler_actions(handler, observation)
                observation = self.observer.capture()
            if not matched:
                break
        return observation

    def _collect_handlers(
        self, step: dict[str, Any] | None, spec: dict[str, Any], trigger: str
    ) -> list[dict[str, Any]]:
        handlers: list[dict[str, Any]] = []
        if step:
            handlers.extend(
                [h for h in step.get("on_error", []) if h.get("trigger", "on_error") == trigger]
            )
        handlers.extend(
            [h for h in spec.get("error_handlers", []) if h.get("trigger", "on_error") == trigger]
        )
        return handlers

    def _handler_condition_matches(
        self, handler: dict[str, Any], observation: Observation
    ) -> bool:
        condition = handler.get("when")
        if condition is None:
            return True
        result = evaluate_condition(condition, observation)
        if result is None:
            return False
        return result is True

    def _handle_error(
        self,
        error: SkillError,
        step: dict[str, Any] | None,
        spec: dict[str, Any],
        observation: Observation,
    ) -> HandlerOutcome:
        handler, retry_override = self._find_error_handler(error, step, spec, observation)
        if not handler:
            if step and step.get("optional"):
                return HandlerOutcome(resolution="continue", error=None)
            return HandlerOutcome(resolution="retry")

        success = self._execute_handler_actions(handler, observation)
        if not success:
            handler_error = SkillError(
                code=SkillErrorCode.HANDLER_FAILED,
                message="Error handler failed",
                stage="handler",
                step_id=error.step_id,
                attempt=error.attempt,
            )
            return HandlerOutcome(resolution="abort", error=handler_error)

        resolution = handler.get("resolution") or "retry"
        if resolution == "escalate":
            takeover_message = handler.get("takeover_message", "User intervention required")
            if not self.config.dry_run:
                self.action_handler.execute(
                    {"_metadata": "do", "action": "Take_over", "message": takeover_message},
                    observation.width,
                    observation.height,
                )
            error = error.with_details(takeover_message=takeover_message)
            error.requires_takeover = True
            return HandlerOutcome(resolution="escalate", error=error)

        return HandlerOutcome(resolution=resolution, retry_policy=retry_override, error=error)

    def _find_error_handler(
        self,
        error: SkillError,
        step: dict[str, Any] | None,
        spec: dict[str, Any],
        observation: Observation,
    ) -> tuple[dict[str, Any] | None, RetryPolicy | None]:
        handlers: list[dict[str, Any]] = []
        if step:
            handlers.extend(
                [h for h in step.get("on_error", []) if h.get("trigger", "on_error") == "on_error"]
            )
        handlers.extend(
            [h for h in spec.get("error_handlers", []) if h.get("trigger", "on_error") == "on_error"]
        )

        for handler in handlers:
            codes = handler.get("codes")
            if codes and error.code.value not in codes:
                continue
            error_ids = handler.get("error_ids")
            if error_ids and error.error_id not in error_ids:
                continue
            if handler.get("when"):
                result = evaluate_condition(handler.get("when"), observation)
                if result is not True:
                    continue
            retry_override = None
            if handler.get("retry"):
                retry_override = self._parse_retry_policy(handler.get("retry"), self.config.default_retry)
            return handler, retry_override
        return None, None

    def _execute_handler_actions(
        self, handler: dict[str, Any], observation: Observation
    ) -> bool:
        actions = handler.get("actions", [])
        for action_spec in actions:
            if not isinstance(action_spec, dict):
                continue
            try:
                action = self._build_action(action_spec, observation)
            except SkillError:
                return False
            if self.config.dry_run:
                continue
            result = self.action_handler.execute(action, observation.width, observation.height)
            if not result.success:
                return False
            wait_after_ms = action_spec.get("wait", {}).get("after_ms") if isinstance(action_spec.get("wait"), dict) else None
            if isinstance(wait_after_ms, int) and wait_after_ms > 0:
                time.sleep(wait_after_ms / 1000.0)
            observation = self.observer.capture()
        return True

    def _build_action(self, step: dict[str, Any], observation: Observation) -> dict[str, Any]:
        action_name = step.get("action")
        if not action_name:
            raise SkillError(
                code=SkillErrorCode.UNKNOWN,
                message="Missing action",
                stage="build_action",
                step_id=step.get("id"),
            )

        action: dict[str, Any] = {"_metadata": "do", "action": action_name}

        if action_name in {"Tap", "Double Tap", "Long Press"}:
            point = self._resolve_target(step.get("target"), observation)
            if not point:
                raise SkillError(
                    code=SkillErrorCode.TARGET_NOT_FOUND,
                    message="Target not found",
                    stage="target",
                    step_id=step.get("id"),
                )
            action["element"] = self._absolute_to_relative(point, observation)

        elif action_name == "Swipe":
            start = self._resolve_target(step.get("start"), observation)
            end = self._resolve_target(step.get("end"), observation)
            if not start or not end:
                raise SkillError(
                    code=SkillErrorCode.TARGET_NOT_FOUND,
                    message="Swipe target not found",
                    stage="target",
                    step_id=step.get("id"),
                )
            action["start"] = self._absolute_to_relative(start, observation)
            action["end"] = self._absolute_to_relative(end, observation)

        elif action_name in {"Type", "Type_Name"}:
            action["text"] = step.get("text", "")

        elif action_name == "Launch":
            action["app"] = step.get("app")

        elif action_name == "Wait":
            duration_ms = step.get("duration_ms")
            if isinstance(duration_ms, int):
                action["duration"] = f"{duration_ms / 1000:.1f} seconds"
            else:
                action["duration"] = step.get("duration", "1 seconds")

        elif action_name in {"Back", "Home", "Take_over", "Note", "Call_API", "Interact"}:
            if action_name == "Take_over":
                action["message"] = step.get("message", "User intervention required")

        else:
            raise SkillError(
                code=SkillErrorCode.UNKNOWN,
                message=f"Unsupported action: {action_name}",
                stage="build_action",
                step_id=step.get("id"),
            )

        if step.get("confirm") and action_name in {"Tap", "Double Tap", "Long Press"}:
            action["message"] = step.get("confirm")

        return action

    def _resolve_target(
        self, target: dict[str, Any] | list[int] | None, observation: Observation
    ) -> tuple[int, int] | None:
        if target is None:
            return None
        if isinstance(target, list) and len(target) == 2:
            return self._relative_to_absolute(target, observation)
        if not isinstance(target, dict):
            return None
        target_type = target.get("type", "coords")
        if target_type == "coords":
            coords = target.get("coords") or target.get("point")
            if not coords or not isinstance(coords, list) or len(coords) != 2:
                return None
            coords_type = target.get("coords_type", "relative")
            if coords_type == "absolute":
                point = (int(coords[0]), int(coords[1]))
            elif coords_type == "percent":
                point = (
                    int(coords[0] * observation.width),
                    int(coords[1] * observation.height),
                )
            else:
                point = self._relative_to_absolute(coords, observation)
        elif target_type == "selector":
            selector = target.get("selector")
            if not selector:
                return None
            if not observation.ui_nodes:
                return None
            point = resolve_selector_to_point(observation.ui_nodes, selector)
            if point is None:
                return None
        elif target_type == "bounds":
            bounds = target.get("bounds")
            if not bounds or len(bounds) != 4:
                return None
            left, top, right, bottom = bounds
            point = (int((left + right) / 2), int((top + bottom) / 2))
        else:
            return None

        offset = target.get("offset") if isinstance(target, dict) else None
        if isinstance(offset, list) and len(offset) == 2:
            point = (point[0] + int(offset[0]), point[1] + int(offset[1]))
        return point

    def _relative_to_absolute(self, coords: list[int], observation: Observation) -> tuple[int, int]:
        x = int(coords[0] / 1000 * observation.width)
        y = int(coords[1] / 1000 * observation.height)
        return x, y

    def _absolute_to_relative(
        self, point: tuple[int, int], observation: Observation
    ) -> list[int]:
        x = int(point[0] / observation.width * 1000)
        y = int(point[1] / observation.height * 1000)
        return [x, y]

    def _check_condition_block(
        self,
        block: dict[str, Any] | None,
        observation: Observation,
        stage: str,
        strict: bool,
    ) -> tuple[bool | None, Observation]:
        if block is None:
            return True, observation
        if "condition" in block:
            condition = block.get("condition")
            timeout_ms = int(block.get("timeout_ms", 0))
            poll_interval_ms = int(block.get("poll_interval_ms", 500))
            mode = block.get("mode", "strict")
        else:
            condition = block
            timeout_ms = 0
            poll_interval_ms = 500
            mode = "strict"

        deadline = time.time() + timeout_ms / 1000.0 if timeout_ms else None
        while True:
            result = evaluate_condition(condition, observation)
            if result is True:
                return True, observation
            if result is False:
                if not deadline or time.time() >= deadline:
                    return False, observation
            if result is None:
                if mode == "best_effort":
                    return True, observation
                if not deadline or time.time() >= deadline:
                    return None if strict else True, observation
            if not deadline:
                return result, observation
            time.sleep(poll_interval_ms / 1000.0)
            observation = self.observer.capture()

    def _parse_retry_policy(
        self, spec: dict[str, Any] | None, fallback: RetryPolicy
    ) -> RetryPolicy:
        if not spec:
            return fallback
        return RetryPolicy(
            max_attempts=int(spec.get("max_attempts", fallback.max_attempts)),
            backoff_ms=int(spec.get("backoff_ms", fallback.backoff_ms)),
            backoff_multiplier=float(spec.get("backoff_multiplier", fallback.backoff_multiplier)),
            max_backoff_ms=int(spec.get("max_backoff_ms", fallback.max_backoff_ms)),
            jitter_ms=int(spec.get("jitter_ms", fallback.jitter_ms)),
            on_codes=spec.get("on_codes", fallback.on_codes),
        )

    def _should_retry(self, error: SkillError, retry_policy: RetryPolicy, attempt: int) -> bool:
        if attempt >= retry_policy.max_attempts:
            return False
        if retry_policy.on_codes is None:
            return True
        return error.code.value in retry_policy.on_codes

    def _backoff(self, attempt: int, retry_policy: RetryPolicy) -> None:
        if retry_policy.backoff_ms <= 0:
            return
        sleep_with_backoff(
            attempt=attempt,
            base_ms=retry_policy.backoff_ms,
            multiplier=retry_policy.backoff_multiplier,
            max_ms=retry_policy.max_backoff_ms or retry_policy.backoff_ms,
            jitter_ms=retry_policy.jitter_ms,
        )

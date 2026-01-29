"""Fast reaction system (System 1) for COTA."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Any

from phone_agent.actions import ActionHandler, ActionResult


@dataclass
class MotionProfile:
    name: str
    duration_range_ms: tuple[int, int]


class MotionLibrary:
    def __init__(self) -> None:
        self._profiles = {
            "fast_skip": MotionProfile("fast_skip", (150, 250)),
            "slow_browse": MotionProfile("slow_browse", (400, 600)),
            "hesitate": MotionProfile("hesitate", (800, 1200)),
        }

    def pick(self, style: str | None) -> MotionProfile:
        if style and style in self._profiles:
            return self._profiles[style]
        return self._profiles["slow_browse"]


class FastActionSystem:
    """Executes atomic intents quickly with light jitter and timing control."""

    def __init__(
        self,
        action_handler: ActionHandler,
        config: Any,
        device_id: str | None = None,
    ) -> None:
        self.action_handler = action_handler
        self.config = config
        self.device_id = device_id
        self._rng = random.Random(getattr(config, "random_seed", None))
        self._motion = MotionLibrary()
        self._last_liveness = 0.0

    def execute_intent(self, intent: Any, observation: Any) -> ActionResult | None:
        observation = observation or _FallbackObservation()
        action = self._build_action(intent, observation)
        if not action:
            return None
        return self.action_handler.execute(action, observation.width, observation.height)

    def maintain_liveness(self, observation: Any) -> None:
        observation = observation or _FallbackObservation()
        if not getattr(self.config, "enable_liveness", False):
            return
        now = time.time()
        interval = getattr(self.config, "liveness_interval_s", 2.0)
        if now - self._last_liveness < interval:
            return
        self._last_liveness = now
        # Default to a short wait to keep the UI active without intrusive actions.
        wait_s = self._rng.uniform(0.3, 0.8)
        action = {"_metadata": "do", "action": "Wait", "duration": f"{wait_s:.2f} seconds"}
        self.action_handler.execute(action, observation.width, observation.height)

    def _build_action(self, intent: Any, observation: Any) -> dict[str, Any] | None:
        observation = observation or _FallbackObservation()
        if intent is None:
            return None
        name = getattr(intent, "name", None) or ""
        params = getattr(intent, "params", {}) or {}

        if name.lower() in ("tap", "click"):
            element = params.get("element") or params.get("coords")
            if not element:
                return None
            element = self._apply_jitter(element, observation)
            return {"_metadata": "do", "action": "Tap", "element": element}

        if name.lower() == "swipe":
            start = params.get("start")
            end = params.get("end")
            if not start or not end:
                return None
            style = params.get("style") or params.get("intent")
            profile = self._motion.pick(style)
            duration_ms = self._rng.randint(*profile.duration_range_ms)
            start = self._apply_jitter(start, observation)
            end = self._apply_jitter(end, observation)
            return {
                "_metadata": "do",
                "action": "Swipe",
                "start": start,
                "end": end,
                "duration_ms": duration_ms,
            }

        if name.lower() in ("type", "input"):
            text = params.get("text")
            if text is None:
                return None
            return {"_metadata": "do", "action": "Type", "text": text}

        if name.lower() == "wait":
            duration = params.get("duration", "1 seconds")
            return {"_metadata": "do", "action": "Wait", "duration": str(duration)}

        if name.lower() == "back":
            return {"_metadata": "do", "action": "Back"}

        if name.lower() == "home":
            return {"_metadata": "do", "action": "Home"}

        return None

    def _apply_jitter(self, element: list[int] | tuple[int, int], observation: Any) -> list[int]:
        observation = observation or _FallbackObservation()
        if not isinstance(element, (list, tuple)) or len(element) != 2:
            return [0, 0]
        jitter = int(getattr(self.config, "jitter_px", 0))
        if jitter <= 0:
            return [int(element[0]), int(element[1])]
        max_coord = 1000
        if max(element[0], element[1]) > 1000:
            width = int(getattr(observation, "width", 0))
            height = int(getattr(observation, "height", 0))
            max_coord = max(width, height, 1)
        dx = self._rng.randint(-jitter, jitter)
        dy = self._rng.randint(-jitter, jitter)
        x = max(0, min(max_coord, int(element[0]) + dx))
        y = max(0, min(max_coord, int(element[1]) + dy))
        return [x, y]


class _FallbackObservation:
    width = 1000
    height = 1000

"""Configuration for the COTA coordinator."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from phone_agent.cota.vlm_analyzer import VLMAnalyzerConfig


@dataclass
class System1Config:
    fps: float = 30.0
    liveness_interval_s: float = 2.0
    jitter_px: int = 6
    chaos_rate: float = 0.05
    enable_liveness: bool = False
    random_seed: int | None = None


@dataclass
class System2Config:
    fps: float = 1.0
    min_latency_ms: int = 500
    max_latency_ms: int = 3000
    enable_skill_routing: bool = True
    enable_exception_skills: bool = True
    enable_vlm_recovery: bool = False
    vlm_confidence_threshold: float = 0.65


@dataclass
class SkillLayerConfig:
    atomic_level: int = 1
    flow_level: int = 2
    recovery_level: int = 3
    level_field: str = "level"
    owner_field: str = "owner"
    role_field: str = "role"


@dataclass
class COTAConfig:
    system1: System1Config = field(default_factory=System1Config)
    system2: System2Config = field(default_factory=System2Config)
    skill_layers: SkillLayerConfig = field(default_factory=SkillLayerConfig)
    vlm_analyzer: VLMAnalyzerConfig | None = None
    exception_skill_map: dict[str, str] = field(
        default_factory=lambda: {
            "SCREEN_MISMATCH": "adapt_ui_change",
            "TARGET_NOT_FOUND": "adapt_ui_change",
            "ACTION_FAILED": "handle_interaction_error",
            "ACTION_EXCEPTION": "handle_device_error",
            "DEVICE_ERROR": "handle_device_error",
            "POSTCONDITION_FAILED": "handle_postcondition_error",
            "TIMEOUT": "handle_postcondition_error",
            "ERROR_SCREEN_DETECTED": "handle_interaction_error",
        }
    )
    extra: dict[str, Any] = field(default_factory=dict)

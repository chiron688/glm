"""COTA-enabled Phone Agent wrapper."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Callable

from phone_agent.actions import ActionHandler
from phone_agent.agent import AgentConfig, PhoneAgent
from phone_agent.model import ModelConfig
from phone_agent.skills import SkillRegistry, SkillRunner, SkillRunnerConfig, SkillRouter, SkillRouterConfig

from phone_agent.cota.config import COTAConfig
from phone_agent.cota.coordinator import COTACoordinator
from phone_agent.cota.system1 import FastActionSystem
from phone_agent.cota.system2 import SlowPlannerSystem
from phone_agent.cota.vlm_analyzer import VLMAnalyzerConfig, VLMExceptionAnalyzer


class COTAPhoneAgent:
    """Phone Agent with COTA dual-system coordination."""

    def __init__(
        self,
        model_config: ModelConfig | None = None,
        agent_config: AgentConfig | None = None,
        cota_config: COTAConfig | None = None,
        confirmation_callback: Callable[[str], bool] | None = None,
        takeover_callback: Callable[[str], None] | None = None,
        skill_registry: SkillRegistry | None = None,
        skill_runner_config: SkillRunnerConfig | None = None,
        skill_router: SkillRouter | None = None,
    ) -> None:
        self.model_config = model_config or ModelConfig()
        self.agent_config = agent_config or AgentConfig()
        self.cota_config = cota_config or COTAConfig()

        self.action_handler = ActionHandler(
            device_id=self.agent_config.device_id,
            confirmation_callback=confirmation_callback,
            takeover_callback=takeover_callback,
        )

        self.skill_registry = skill_registry
        skill_paths = self.agent_config.skill_paths
        if skill_paths is None and self.cota_config.system2.enable_skill_routing:
            skill_paths = ["skills"]

        if self.skill_registry is None and skill_paths:
            registry = SkillRegistry()
            registry.load_from_paths(skill_paths)
            self.skill_registry = registry

        self.skill_runner = None
        if self.skill_registry is not None:
            runner_config = skill_runner_config or SkillRunnerConfig(
                common_error_handlers_path=self.agent_config.skill_common_handlers_path,
                record_dir=self.agent_config.skill_record_dir,
                playback_dir=self.agent_config.skill_playback_dir,
            )
            self.skill_runner = SkillRunner(
                self.skill_registry,
                config=runner_config,
                device_id=self.agent_config.device_id,
                action_handler=self.action_handler,
            )

        self.skill_router = skill_router
        if self.skill_router is None and self.skill_registry is not None:
            router_config = SkillRouterConfig(
                enforce_skill_whitelist=bool(self.agent_config.skill_whitelist),
                skill_whitelist=self.agent_config.skill_whitelist or [],
                enforce_on_risk=self.agent_config.skill_risk_gate_enabled,
                risk_keywords=self.agent_config.skill_risk_keywords or [],
            )
            self.skill_router = SkillRouter(self.skill_registry, router_config)

        fallback_agent_config = replace(
            self.agent_config, enable_skill_routing=False, skill_paths=None
        )
        self.llm_agent = PhoneAgent(
            model_config=self.model_config,
            agent_config=fallback_agent_config,
            confirmation_callback=confirmation_callback,
            takeover_callback=takeover_callback,
        )

        self.system1 = FastActionSystem(
            action_handler=self.action_handler,
            config=self.cota_config.system1,
            device_id=self.agent_config.device_id,
        )
        vlm_analyzer = None
        if self.cota_config.system2.enable_vlm_recovery:
            analyzer_config = self.cota_config.vlm_analyzer or VLMAnalyzerConfig.from_model_config(
                self.model_config
            )
            vlm_analyzer = VLMExceptionAnalyzer(analyzer_config)
        self.system2 = SlowPlannerSystem(
            config=self.cota_config,
            skill_registry=self.skill_registry,
            skill_router=self.skill_router,
            llm_agent=self.llm_agent,
            vlm_analyzer=vlm_analyzer,
        )

        self.coordinator = COTACoordinator(
            system1=self.system1,
            system2=self.system2,
            skill_runner=self.skill_runner,
            observer=self.skill_runner.observer if self.skill_runner else None,
        )

    def run(self, task: str) -> str:
        return self.coordinator.run(task)

    def reset(self) -> None:
        self.llm_agent.reset()

    @property
    def skill_errors(self) -> list[str]:
        if not self.skill_registry:
            return []
        return self.skill_registry.errors

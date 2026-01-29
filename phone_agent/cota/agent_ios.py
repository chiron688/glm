"""COTA-enabled iOS agent."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from phone_agent.actions.handler_ios import IOSActionHandler
from phone_agent.cota.config import COTAConfig
from phone_agent.cota.coordinator import COTACoordinator
from phone_agent.cota.system1 import FastActionSystem
from phone_agent.cota.system2 import SlowPlannerSystem
from phone_agent.cota.vlm_analyzer import VLMAnalyzerConfig, VLMExceptionAnalyzer
from phone_agent.model import ModelConfig
import os

from phone_agent.skills import (
    IOSObservationProvider,
    build_ocr_provider,
    SkillLearningRecorder,
    SkillRegistry,
    SkillRunner,
    SkillRunnerConfig,
    SkillRouter,
    SkillRouterConfig,
)
from phone_agent.xctest import XCTestConnection


@dataclass
class COTAIOSAgentConfig:
    max_steps: int = 100
    wda_url: str = "http://localhost:8100"
    session_id: str | None = None
    device_id: str | None = None
    lang: str = "cn"
    verbose: bool = True
    skill_paths: list[str] | None = None
    enable_skill_routing: bool = True
    skill_common_handlers_path: str | None = None
    skill_record_dir: str | None = None
    skill_playback_dir: str | None = None
    skill_whitelist: list[str] | None = None
    skill_risk_gate_enabled: bool = False
    skill_risk_keywords: list[str] | None = None
    use_ocr: bool = True
    ocr_lang: str = "ml"

    def __post_init__(self):
        """补齐默认风险关键词，保证路由与风控可用。"""
        # 关键步骤：设置默认风险关键词（iOS COTA 代理）
        if self.skill_risk_keywords is None:
            self.skill_risk_keywords = ["发布", "上传", "post", "upload", "publish"]


class COTAIOSAgent:
    """基于 COTA 的 iOS 自动化代理（WDA）。"""

    def __init__(
        self,
        model_config: ModelConfig | None = None,
        agent_config: COTAIOSAgentConfig | None = None,
        cota_config: COTAConfig | None = None,
        confirmation_callback: Callable[[str], bool] | None = None,
        takeover_callback: Callable[[str], None] | None = None,
        skill_registry: SkillRegistry | None = None,
        skill_runner_config: SkillRunnerConfig | None = None,
        skill_router: SkillRouter | None = None,
    ) -> None:
        """初始化 iOS COTA 代理，构建 WDA、Skills 与双系统协同。"""
        # 关键步骤：初始化依赖并装配系统（iOS COTA 代理）
        self.model_config = model_config or ModelConfig()
        self.agent_config = agent_config or COTAIOSAgentConfig()
        self.cota_config = cota_config or COTAConfig()
        self.learning_recorder = SkillLearningRecorder.from_env()

        # Ensure WDA session
        self.wda_connection = XCTestConnection(wda_url=self.agent_config.wda_url)
        if self.agent_config.session_id is None:
            success, session_id = self.wda_connection.start_wda_session()
            if success and session_id != "session_started":
                self.agent_config.session_id = session_id
                if self.agent_config.verbose:
                    print(f"✅ Created WDA session: {session_id}")
            elif self.agent_config.verbose:
                print("⚠️  Using default WDA session (no explicit session ID)")

        self.action_handler = IOSActionHandler(
            wda_url=self.agent_config.wda_url,
            session_id=self.agent_config.session_id,
            confirmation_callback=confirmation_callback,
            takeover_callback=takeover_callback,
        )

        self.skill_registry = skill_registry
        skill_paths = self.agent_config.skill_paths
        if skill_paths is None and self.agent_config.enable_skill_routing:
            skill_paths = ["skills"]

        if self.skill_registry is None and skill_paths:
            registry = SkillRegistry()
            registry.load_from_paths(skill_paths)
            self.skill_registry = registry

        runner_config = skill_runner_config or SkillRunnerConfig(
            common_error_handlers_path=self.agent_config.skill_common_handlers_path,
            record_dir=self.agent_config.skill_record_dir,
            playback_dir=self.agent_config.skill_playback_dir,
        )
        if self.agent_config.use_ocr and runner_config.ocr_provider is None:
            provider = os.getenv("PHONE_AGENT_OCR_PROVIDER", "paddle")
            if provider.lower() in ("gemma", "google-gemma"):
                runner_config.ocr_provider = build_ocr_provider(
                    provider,
                    base_url=os.getenv("PHONE_AGENT_OCR_BASE_URL", self.model_config.base_url),
                    api_key=os.getenv("PHONE_AGENT_OCR_API_KEY", self.model_config.api_key),
                    model_name=os.getenv(
                        "PHONE_AGENT_OCR_MODEL",
                        "google/gemma-3n-E2B-it-litert-lm",
                    ),
                )
            else:
                runner_config.ocr_provider = build_ocr_provider(
                    provider,
                    lang=os.getenv("PHONE_AGENT_OCR_LANG", self.agent_config.ocr_lang),
                    force_v5=True,
                )

        observer = IOSObservationProvider(
            wda_url=self.agent_config.wda_url,
            session_id=self.agent_config.session_id,
            device_id=self.agent_config.device_id,
            include_screen_hash=runner_config.include_screen_hash,
            ocr_provider=runner_config.ocr_provider,
        )

        self.skill_runner = None
        if self.skill_registry is not None:
            self.skill_runner = SkillRunner(
                self.skill_registry,
                config=runner_config,
                device_id=self.agent_config.device_id,
                action_handler=self.action_handler,
                observer=observer,
                learning_recorder=self.learning_recorder,
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
            llm_agent=None,
            vlm_analyzer=vlm_analyzer,
            learning_recorder=self.learning_recorder,
        )

        self.coordinator = COTACoordinator(
            system1=self.system1,
            system2=self.system2,
            skill_runner=self.skill_runner,
            observer=observer,
        )

    def run(self, task: str) -> str:
        """执行任务，交由协调器推进计划与技能步骤。"""
        # 关键步骤：委派到协调器执行（iOS COTA 代理）
        return self.coordinator.run(task)

    def reset(self) -> None:
        """iOS COTA 为无状态重置预留接口。"""
        # 关键步骤：重置占位（iOS COTA 代理）
        return

    @property
    def skill_errors(self) -> list[str]:
        """返回技能加载与解析时的错误列表。"""
        # 关键步骤：汇总技能错误（iOS COTA 代理）
        if not self.skill_registry:
            return []
        return self.skill_registry.errors

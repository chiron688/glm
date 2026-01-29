"""
Phone Agent - AI 驱动的手机自动化框架。

本包提供用于自动化 Android 与 iOS 手机交互的工具，
利用 AI 模型进行视觉理解与决策。
"""

from phone_agent.agent import PhoneAgent
from phone_agent.agent_ios import IOSPhoneAgent
from phone_agent.skills import (
    SkillError,
    SkillErrorCode,
    SkillRouter,
    SkillRouterConfig,
    SkillRegistry,
    SkillRunner,
    SkillRunnerConfig,
    SkillSchemaError,
    OcrProvider,
    TesseractOcrProvider,
)
from phone_agent.cota import (
    COTAPhoneAgent,
    COTAIOSAgent,
    COTAIOSAgentConfig,
    COTAConfig,
    COTACoordinator,
    FastActionSystem,
    SlowPlannerSystem,
)

__version__ = "0.1.0"
__all__ = [
    "PhoneAgent",
    "IOSPhoneAgent",
    "COTAPhoneAgent",
    "COTAIOSAgent",
    "COTAIOSAgentConfig",
    "COTAConfig",
    "COTACoordinator",
    "FastActionSystem",
    "SlowPlannerSystem",
    "SkillError",
    "SkillErrorCode",
    "SkillRouter",
    "SkillRouterConfig",
    "SkillRegistry",
    "SkillRunner",
    "SkillRunnerConfig",
    "SkillSchemaError",
    "OcrProvider",
    "TesseractOcrProvider",
]

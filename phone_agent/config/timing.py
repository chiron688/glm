"""Phone Agent 的时间配置。

本模块定义应用中可配置的所有等待时间。
用户可通过修改本文件或设置环境变量来自定义这些值。
"""

import os
from dataclasses import dataclass


@dataclass
class ActionTimingConfig:
    """动作处理的时间延迟配置。"""

    # 文本输入相关延迟（秒）
    keyboard_switch_delay: float = 1.0  # 切换到 ADB 键盘后的延迟
    text_clear_delay: float = 1.0  # 清空文本后的延迟
    text_input_delay: float = 1.0  # 输入文本后的延迟
    keyboard_restore_delay: float = 1.0  # 恢复原始键盘后的延迟

    def __post_init__(self):
        """若存在环境变量则加载其值。"""
        self.keyboard_switch_delay = float(
            os.getenv("PHONE_AGENT_KEYBOARD_SWITCH_DELAY", self.keyboard_switch_delay)
        )
        self.text_clear_delay = float(
            os.getenv("PHONE_AGENT_TEXT_CLEAR_DELAY", self.text_clear_delay)
        )
        self.text_input_delay = float(
            os.getenv("PHONE_AGENT_TEXT_INPUT_DELAY", self.text_input_delay)
        )
        self.keyboard_restore_delay = float(
            os.getenv("PHONE_AGENT_KEYBOARD_RESTORE_DELAY", self.keyboard_restore_delay)
        )


@dataclass
class DeviceTimingConfig:
    """设备操作的时间延迟配置。"""

    # 各类设备操作的默认延迟（秒）
    default_tap_delay: float = 1.0  # 点击后的默认延迟
    default_double_tap_delay: float = 1.0  # 双击后的默认延迟
    double_tap_interval: float = 0.1  # 双击两次点击的间隔
    default_long_press_delay: float = 1.0  # 长按后的默认延迟
    default_swipe_delay: float = 1.0  # 滑动后的默认延迟
    default_back_delay: float = 1.0  # 返回后的默认延迟
    default_home_delay: float = 1.0  # 回到桌面后的默认延迟
    default_launch_delay: float = 1.0  # 启动应用后的默认延迟

    def __post_init__(self):
        """若存在环境变量则加载其值。"""
        self.default_tap_delay = float(
            os.getenv("PHONE_AGENT_TAP_DELAY", self.default_tap_delay)
        )
        self.default_double_tap_delay = float(
            os.getenv("PHONE_AGENT_DOUBLE_TAP_DELAY", self.default_double_tap_delay)
        )
        self.double_tap_interval = float(
            os.getenv("PHONE_AGENT_DOUBLE_TAP_INTERVAL", self.double_tap_interval)
        )
        self.default_long_press_delay = float(
            os.getenv("PHONE_AGENT_LONG_PRESS_DELAY", self.default_long_press_delay)
        )
        self.default_swipe_delay = float(
            os.getenv("PHONE_AGENT_SWIPE_DELAY", self.default_swipe_delay)
        )
        self.default_back_delay = float(
            os.getenv("PHONE_AGENT_BACK_DELAY", self.default_back_delay)
        )
        self.default_home_delay = float(
            os.getenv("PHONE_AGENT_HOME_DELAY", self.default_home_delay)
        )
        self.default_launch_delay = float(
            os.getenv("PHONE_AGENT_LAUNCH_DELAY", self.default_launch_delay)
        )


@dataclass
class ConnectionTimingConfig:
    """ADB 连接的时间延迟配置。"""

    # ADB 服务与连接延迟（秒）
    adb_restart_delay: float = 2.0  # 启用 TCP/IP 模式后的等待时间
    server_restart_delay: float = (
        1.0  # 杀死与启动 ADB 服务之间的等待时间
    )

    def __post_init__(self):
        """若存在环境变量则加载其值。"""
        self.adb_restart_delay = float(
            os.getenv("PHONE_AGENT_ADB_RESTART_DELAY", self.adb_restart_delay)
        )
        self.server_restart_delay = float(
            os.getenv("PHONE_AGENT_SERVER_RESTART_DELAY", self.server_restart_delay)
        )


@dataclass
class TimingConfig:
    """组合所有时间设置的总配置。"""

    action: ActionTimingConfig
    device: DeviceTimingConfig
    connection: ConnectionTimingConfig

    def __init__(self):
        """初始化所有时间配置。"""
        self.action = ActionTimingConfig()
        self.device = DeviceTimingConfig()
        self.connection = ConnectionTimingConfig()


# 全局时间配置实例
# 用户可在运行时或通过环境变量修改这些值
TIMING_CONFIG = TimingConfig()


def get_timing_config() -> TimingConfig:
    """
    获取全局时间配置。

    返回:
        全局 TimingConfig 实例。
    """
    return TIMING_CONFIG


def update_timing_config(
    action: ActionTimingConfig | None = None,
    device: DeviceTimingConfig | None = None,
    connection: ConnectionTimingConfig | None = None,
) -> None:
    """
    更新全局时间配置。

    参数:
        action: 新的动作时间配置。
        device: 新的设备时间配置。
        connection: 新的连接时间配置。

    示例:
        >>> from phone_agent.config.timing import update_timing_config, ActionTimingConfig
        >>> custom_action = ActionTimingConfig(
        ...     keyboard_switch_delay=0.5,
        ...     text_input_delay=0.5
        ... )
        >>> update_timing_config(action=custom_action)
    """
    global TIMING_CONFIG
    if action is not None:
        TIMING_CONFIG.action = action
    if device is not None:
        TIMING_CONFIG.device = device
    if connection is not None:
        TIMING_CONFIG.connection = connection


__all__ = [
    "ActionTimingConfig",
    "DeviceTimingConfig",
    "ConnectionTimingConfig",
    "TimingConfig",
    "TIMING_CONFIG",
    "get_timing_config",
    "update_timing_config",
]

"""通过 WebDriverAgent/XCUITest 进行 iOS 设备交互的 XCTest 工具。"""

from phone_agent.xctest.connection import (
    ConnectionType,
    DeviceInfo,
    XCTestConnection,
    list_devices,
    quick_connect,
)
from phone_agent.xctest.device import (
    back,
    double_tap,
    get_current_app,
    home,
    launch_app,
    long_press,
    swipe,
    tap,
)
from phone_agent.xctest.input import (
    clear_text,
    type_text,
)
from phone_agent.xctest.screenshot import get_screenshot

__all__ = [
    # 截图
    "get_screenshot",
    # 输入
    "type_text",
    "clear_text",
    # 设备控制
    "get_current_app",
    "tap",
    "swipe",
    "back",
    "home",
    "double_tap",
    "long_press",
    "launch_app",
    # 连接管理
    "XCTestConnection",
    "DeviceInfo",
    "ConnectionType",
    "quick_connect",
    "list_devices",
]

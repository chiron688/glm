"""通过 WebDriverAgent 进行 iOS 自动化的设备控制工具。"""

import subprocess
import time
from typing import Optional

from phone_agent.config.apps_ios import APP_PACKAGES_IOS as APP_PACKAGES

SCALE_FACTOR = 3  # 多数新款 iPhone 使用 3

def _get_wda_session_url(wda_url: str, session_id: str | None, endpoint: str) -> str:
    """
    获取会话端点对应的正确 WDA URL。

    参数:
        wda_url: WDA 基础地址。
        session_id: 可选的会话 ID。
        endpoint: 端点路径。

    返回:
        端点的完整 URL。
    """
    base = wda_url.rstrip("/")
    if session_id:
        return f"{base}/session/{session_id}/{endpoint}"
    else:
        # 尽量在无需 session 时使用 WDA 端点
        return f"{base}/{endpoint}"


def get_current_app(
    wda_url: str = "http://localhost:8100", session_id: str | None = None
) -> str:
    """
    获取当前前台应用的 bundle ID 和名称。

    参数:
        wda_url: WebDriverAgent 地址。
        session_id: 可选的 WDA 会话 ID。

    返回:
        若可识别则返回应用名称，否则返回 "System Home"。
    """
    try:
        import requests

        # 通过 activeAppInfo 端点从 WDA 获取当前应用信息
        response = requests.get(
            f"{wda_url.rstrip('/')}/wda/activeAppInfo", timeout=5, verify=False
        )

        if response.status_code == 200:
            data = response.json()
            # 从响应中提取 bundle ID
            # 响应格式: {"value": {"bundleId": "com.apple.AppStore", "name": "", "pid": 825, "processArguments": {...}}, "sessionId": "..."}
            value = data.get("value", {})
            bundle_id = value.get("bundleId", "")

            if bundle_id:
                # 根据 bundle ID 尝试匹配应用名称
                for app_name, package in APP_PACKAGES.items():
                    if package == bundle_id:
                        return app_name

            return "System Home"

    except ImportError:
        print("Error: requests library required. Install: pip install requests")
    except Exception as e:
        print(f"Error getting current app: {e}")

    return "System Home"


def tap(
    x: int,
    y: int,
    wda_url: str = "http://localhost:8100",
    session_id: str | None = None,
    delay: float = 1.0,
) -> None:
    """
    使用 WebDriver W3C Actions API 在指定坐标点击。

    参数:
        x: X 坐标。
        y: Y 坐标。
        wda_url: WebDriverAgent 地址。
        session_id: 可选的 WDA 会话 ID。
        delay: 点击后的延迟（秒）。
    """
    try:
        import requests

        url = _get_wda_session_url(wda_url, session_id, "actions")

        # 用于点击的 W3C WebDriver Actions API
        actions = {
            "actions": [
                {
                    "type": "pointer",
                    "id": "finger1",
                    "parameters": {"pointerType": "touch"},
                    "actions": [
                        {"type": "pointerMove", "duration": 0, "x": x / SCALE_FACTOR, "y": y / SCALE_FACTOR},
                        {"type": "pointerDown", "button": 0},
                        {"type": "pause", "duration": 0.1},
                        {"type": "pointerUp", "button": 0},
                    ],
                }
            ]
        }

        requests.post(url, json=actions, timeout=15, verify=False)

        time.sleep(delay)

    except ImportError:
        print("Error: requests library required. Install: pip install requests")
    except Exception as e:
        print(f"Error tapping: {e}")


def double_tap(
    x: int,
    y: int,
    wda_url: str = "http://localhost:8100",
    session_id: str | None = None,
    delay: float = 1.0,
) -> None:
    """
    使用 WebDriver W3C Actions API 在指定坐标双击。

    参数:
        x: X 坐标。
        y: Y 坐标。
        wda_url: WebDriverAgent 地址。
        session_id: 可选的 WDA 会话 ID。
        delay: 双击后的延迟（秒）。
    """
    try:
        import requests

        url = _get_wda_session_url(wda_url, session_id, "actions")

        # 用于双击的 W3C WebDriver Actions API
        actions = {
            "actions": [
                {
                    "type": "pointer",
                    "id": "finger1",
                    "parameters": {"pointerType": "touch"},
                    "actions": [
                        {"type": "pointerMove", "duration": 0, "x": x / SCALE_FACTOR, "y": y / SCALE_FACTOR},
                        {"type": "pointerDown", "button": 0},
                        {"type": "pause", "duration": 100},
                        {"type": "pointerUp", "button": 0},
                        {"type": "pause", "duration": 100},
                        {"type": "pointerDown", "button": 0},
                        {"type": "pause", "duration": 100},
                        {"type": "pointerUp", "button": 0},
                    ],
                }
            ]
        }

        requests.post(url, json=actions, timeout=10, verify=False)

        time.sleep(delay)

    except ImportError:
        print("Error: requests library required. Install: pip install requests")
    except Exception as e:
        print(f"Error double tapping: {e}")


def long_press(
    x: int,
    y: int,
    duration: float = 3.0,
    wda_url: str = "http://localhost:8100",
    session_id: str | None = None,
    delay: float = 1.0,
) -> None:
    """
    使用 WebDriver W3C Actions API 在指定坐标长按。

    参数:
        x: X 坐标。
        y: Y 坐标。
        duration: 长按持续时间（秒）。
        wda_url: WebDriverAgent 地址。
        session_id: 可选的 WDA 会话 ID。
        delay: 长按后的延迟（秒）。
    """
    try:
        import requests

        url = _get_wda_session_url(wda_url, session_id, "actions")

        # 用于长按的 W3C WebDriver Actions API
        # 将持续时间转换为毫秒
        duration_ms = int(duration * 1000)

        actions = {
            "actions": [
                {
                    "type": "pointer",
                    "id": "finger1",
                    "parameters": {"pointerType": "touch"},
                    "actions": [
                        {"type": "pointerMove", "duration": 0, "x": x / SCALE_FACTOR, "y": y / SCALE_FACTOR},
                        {"type": "pointerDown", "button": 0},
                        {"type": "pause", "duration": duration_ms},
                        {"type": "pointerUp", "button": 0},
                    ],
                }
            ]
        }

        requests.post(url, json=actions, timeout=int(duration + 10), verify=False)

        time.sleep(delay)

    except ImportError:
        print("Error: requests library required. Install: pip install requests")
    except Exception as e:
        print(f"Error long pressing: {e}")


def swipe(
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    duration: float | None = None,
    wda_url: str = "http://localhost:8100",
    session_id: str | None = None,
    delay: float = 1.0,
) -> None:
    """
    使用 WDA 的 dragfromtoforduration 端点从起点滑动到终点。

    参数:
        start_x: 起点 X 坐标。
        start_y: 起点 Y 坐标。
        end_x: 终点 X 坐标。
        end_y: 终点 Y 坐标。
        duration: 滑动持续时间（秒，None 时自动计算）。
        wda_url: WebDriverAgent 地址。
        session_id: 可选的 WDA 会话 ID。
        delay: 滑动后的延迟（秒）。
    """
    try:
        import requests

        if duration is None:
            # 根据距离计算持续时间
            dist_sq = (start_x - end_x) ** 2 + (start_y - end_y) ** 2
            duration = dist_sq / 1000000  # 换算为秒
            duration = max(0.3, min(duration, 2.0))  # 限制在 0.3-2 秒之间

        url = _get_wda_session_url(wda_url, session_id, "wda/dragfromtoforduration")

        # WDA dragfromtoforduration API 请求体
        payload = {
            "fromX": start_x / SCALE_FACTOR,
            "fromY": start_y / SCALE_FACTOR,
            "toX": end_x / SCALE_FACTOR,
            "toY": end_y / SCALE_FACTOR,
            "duration": duration,
        }

        requests.post(url, json=payload, timeout=int(duration + 10), verify=False)

        time.sleep(delay)

    except ImportError:
        print("Error: requests library required. Install: pip install requests")
    except Exception as e:
        print(f"Error swiping: {e}")


def back(
    wda_url: str = "http://localhost:8100",
    session_id: str | None = None,
    delay: float = 1.0,
) -> None:
    """
    返回上一页（从左边缘滑动）。

    参数:
        wda_url: WebDriverAgent 地址。
        session_id: 可选的 WDA 会话 ID。
        delay: 返回后的延迟（秒）。

    说明:
        iOS 没有通用的返回按钮，这里通过从屏幕左边缘滑动模拟返回手势。
    """
    try:
        import requests

        url = _get_wda_session_url(wda_url, session_id, "wda/dragfromtoforduration")

        # 从左边缘滑动以模拟返回手势
        payload = {
            "fromX": 0,
            "fromY": 640,
            "toX": 400,
            "toY": 640,
            "duration": 0.3,
        }

        requests.post(url, json=payload, timeout=10, verify=False)

        time.sleep(delay)

    except ImportError:
        print("Error: requests library required. Install: pip install requests")
    except Exception as e:
        print(f"Error performing back gesture: {e}")


def home(
    wda_url: str = "http://localhost:8100",
    session_id: str | None = None,
    delay: float = 1.0,
) -> None:
    """
    按下 Home 键。

    参数:
        wda_url: WebDriverAgent 地址。
        session_id: 可选的 WDA 会话 ID。
        delay: 按下后的延迟（秒）。
    """
    try:
        import requests

        url = f"{wda_url.rstrip('/')}/wda/homescreen"

        requests.post(url, timeout=10, verify=False)

        time.sleep(delay)

    except ImportError:
        print("Error: requests library required. Install: pip install requests")
    except Exception as e:
        print(f"Error pressing home: {e}")


def launch_app(
    app_name: str,
    wda_url: str = "http://localhost:8100",
    session_id: str | None = None,
    delay: float = 1.0,
) -> bool:
    """
    根据应用名称启动应用。

    参数:
        app_name: 应用名称（必须存在于 APP_PACKAGES）。
        wda_url: WebDriverAgent 地址。
        session_id: 可选的 WDA 会话 ID。
        delay: 启动后的延迟（秒）。

    返回:
        启动成功返回 True，未找到应用返回 False。
    """
    if app_name not in APP_PACKAGES:
        return False

    try:
        import requests

        bundle_id = APP_PACKAGES[app_name]
        url = _get_wda_session_url(wda_url, session_id, "wda/apps/launch")

        response = requests.post(
            url, json={"bundleId": bundle_id}, timeout=10, verify=False
        )

        time.sleep(delay)
        return response.status_code in (200, 201)

    except ImportError:
        print("Error: requests library required. Install: pip install requests")
        return False
    except Exception as e:
        print(f"Error launching app: {e}")
        return False


def get_screen_size(
    wda_url: str = "http://localhost:8100", session_id: str | None = None
) -> tuple[int, int]:
    """
    获取屏幕尺寸。

    参数:
        wda_url: WebDriverAgent 地址。
        session_id: 可选的 WDA 会话 ID。

    返回:
        (width, height) 元组。若无法获取则默认返回 (375, 812)。
    """
    try:
        import requests

        url = _get_wda_session_url(wda_url, session_id, "window/size")

        response = requests.get(url, timeout=5, verify=False)

        if response.status_code == 200:
            data = response.json()
            value = data.get("value", {})
            width = value.get("width", 375)
            height = value.get("height", 812)
            return width, height

    except ImportError:
        print("Error: requests library required. Install: pip install requests")
    except Exception as e:
        print(f"Error getting screen size: {e}")

    # 默认的 iPhone 屏幕尺寸（iPhone X 及以后）
    return 375, 812


def press_button(
    button_name: str,
    wda_url: str = "http://localhost:8100",
    session_id: str | None = None,
    delay: float = 1.0,
) -> None:
    """
    按下实体按键。

    参数:
        button_name: 按键名称（例如 "home"、"volumeUp"、"volumeDown"）。
        wda_url: WebDriverAgent 地址。
        session_id: 可选的 WDA 会话 ID。
        delay: 按下后的延迟（秒）。
    """
    try:
        import requests

        url = f"{wda_url.rstrip('/')}/wda/pressButton"

        requests.post(url, json={"name": button_name}, timeout=10, verify=False)

        time.sleep(delay)

    except ImportError:
        print("Error: requests library required. Install: pip install requests")
    except Exception as e:
        print(f"Error pressing button: {e}")

"""用于捕获 iOS 设备屏幕的截图工具。"""

import base64
import os
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from io import BytesIO

from PIL import Image


@dataclass
class Screenshot:
    """表示一次捕获的截图。"""

    base64_data: str
    width: int
    height: int
    is_sensitive: bool = False


def get_screenshot(
    wda_url: str = "http://localhost:8100",
    session_id: str | None = None,
    device_id: str | None = None,
    timeout: int = 10,
) -> Screenshot:
    """
    从连接的 iOS 设备获取截图。

    参数:
        wda_url: WebDriverAgent 地址。
        session_id: 可选的 WDA 会话 ID。
        device_id: 可选的设备 UDID（用于 idevicescreenshot 兜底）。
        timeout: 截图操作的超时时间（秒）。

    返回:
        包含 base64 数据和尺寸的 Screenshot 对象。

    说明:
        优先使用 WebDriverAgent，若不可用则回退到 idevicescreenshot。
        若都失败，则返回黑色占位图。
    """
    # 先尝试 WebDriverAgent（首选方式）
    screenshot = _get_screenshot_wda(wda_url, session_id, timeout)
    if screenshot:
        return screenshot

    # 回退到 idevicescreenshot
    screenshot = _get_screenshot_idevice(device_id, timeout)
    if screenshot:
        return screenshot

    # 返回黑色占位图
    return _create_fallback_screenshot(is_sensitive=False)


def _get_screenshot_wda(
    wda_url: str, session_id: str | None, timeout: int
) -> Screenshot | None:
    """
    使用 WebDriverAgent 捕获截图。

    参数:
        wda_url: WebDriverAgent 地址。
        session_id: 可选的 WDA 会话 ID。
        timeout: 超时时间（秒）。

    返回:
        成功时返回 Screenshot 对象，失败时返回 None。
    """
    try:
        import requests

        url = f"{wda_url.rstrip('/')}/screenshot"

        response = requests.get(url, timeout=timeout, verify=False)

        if response.status_code == 200:
            data = response.json()
            base64_data = data.get("value", "")

            if base64_data:
                # 解码以获取尺寸
                img_data = base64.b64decode(base64_data)
                img = Image.open(BytesIO(img_data))
                width, height = img.size

                return Screenshot(
                    base64_data=base64_data,
                    width=width,
                    height=height,
                    is_sensitive=False,
                )

    except ImportError:
        print("Note: requests library not installed. Install: pip install requests")
    except Exception as e:
        print(f"WDA screenshot failed: {e}")

    return None


def _get_screenshot_idevice(
    device_id: str | None, timeout: int
) -> Screenshot | None:
    """
    使用 idevicescreenshot（libimobiledevice）捕获截图。

    参数:
        device_id: 可选的设备 UDID。
        timeout: 超时时间（秒）。

    返回:
        成功时返回 Screenshot 对象，失败时返回 None。
    """
    try:
        temp_path = os.path.join(
            tempfile.gettempdir(), f"ios_screenshot_{uuid.uuid4()}.png"
        )

        cmd = ["idevicescreenshot"]
        if device_id:
            cmd.extend(["-u", device_id])
        cmd.append(temp_path)

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )

        if result.returncode == 0 and os.path.exists(temp_path):
            # 读取并编码图片
            img = Image.open(temp_path)
            width, height = img.size

            buffered = BytesIO()
            img.save(buffered, format="PNG")
            base64_data = base64.b64encode(buffered.getvalue()).decode("utf-8")

            # 清理临时文件
            os.remove(temp_path)

            return Screenshot(
                base64_data=base64_data, width=width, height=height, is_sensitive=False
            )

    except FileNotFoundError:
        print(
            "Note: idevicescreenshot not found. Install: brew install libimobiledevice"
        )
    except Exception as e:
        print(f"idevicescreenshot failed: {e}")

    return None


def _create_fallback_screenshot(is_sensitive: bool) -> Screenshot:
    """
    截图失败时创建黑色占位图。

    参数:
        is_sensitive: 是否因敏感内容导致失败。

    返回:
        带黑色图片的 Screenshot 对象。
    """
    # 默认的 iPhone 屏幕尺寸（iPhone 14 Pro）
    default_width, default_height = 1179, 2556

    black_img = Image.new("RGB", (default_width, default_height), color="black")
    buffered = BytesIO()
    black_img.save(buffered, format="PNG")
    base64_data = base64.b64encode(buffered.getvalue()).decode("utf-8")

    return Screenshot(
        base64_data=base64_data,
        width=default_width,
        height=default_height,
        is_sensitive=is_sensitive,
    )


def save_screenshot(
    screenshot: Screenshot,
    file_path: str,
) -> bool:
    """
    将截图保存到文件。

    参数:
        screenshot: Screenshot 对象。
        file_path: 保存路径。

    返回:
        成功返回 True，失败返回 False。
    """
    try:
        img_data = base64.b64decode(screenshot.base64_data)
        img = Image.open(BytesIO(img_data))
        img.save(file_path)
        return True
    except Exception as e:
        print(f"Error saving screenshot: {e}")
        return False


def get_screenshot_png(
    wda_url: str = "http://localhost:8100",
    session_id: str | None = None,
    device_id: str | None = None,
) -> bytes | None:
    """
    获取 PNG 格式的截图字节数据。

    参数:
        wda_url: WebDriverAgent 地址。
        session_id: 可选的 WDA 会话 ID。
        device_id: 可选的设备 UDID。

    返回:
        成功返回 PNG 字节数据，失败返回 None。
    """
    screenshot = get_screenshot(wda_url, session_id, device_id)

    try:
        return base64.b64decode(screenshot.base64_data)
    except Exception:
        return None

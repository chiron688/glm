"""通过 WebDriverAgent 进行 iOS 设备文本输入的工具。"""

import time


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


def type_text(
    text: str,
    wda_url: str = "http://localhost:8100",
    session_id: str | None = None,
    frequency: int = 60,
) -> None:
    """
    在当前焦点输入框中输入文本。

    参数:
        text: 要输入的文本。
        wda_url: WebDriverAgent 地址。
        session_id: 可选的 WDA 会话 ID。
        frequency: 输入频率（每分钟按键数），默认 60。

    说明:
        调用前输入框必须已聚焦。
        可先用 tap() 让输入框获得焦点。
    """
    try:
        import requests

        url = _get_wda_session_url(wda_url, session_id, "wda/keys")

        # 向 WDA 发送文本
        response = requests.post(
            url, json={"value": list(text), "frequency": frequency}, timeout=30, verify=False
        )

        if response.status_code not in (200, 201):
            print(f"Warning: Text input may have failed. Status: {response.status_code}")

    except ImportError:
        print("Error: requests library required. Install: pip install requests")
    except Exception as e:
        print(f"Error typing text: {e}")


def clear_text(
    wda_url: str = "http://localhost:8100",
    session_id: str | None = None,
) -> None:
    """
    清空当前焦点输入框中的文本。

    参数:
        wda_url: WebDriverAgent 地址。
        session_id: 可选的 WDA 会话 ID。

    说明:
        该方法会向当前激活元素发送清空命令。
        调用前输入框必须已聚焦。
    """
    try:
        import requests

        # 先尝试获取当前激活元素
        url = _get_wda_session_url(wda_url, session_id, "element/active")

        response = requests.get(url, timeout=10, verify=False)

        if response.status_code == 200:
            data = response.json()
            element_id = data.get("value", {}).get("ELEMENT") or data.get("value", {}).get("element-6066-11e4-a52e-4f735466cecf")

            if element_id:
                # 清空该元素
                clear_url = _get_wda_session_url(wda_url, session_id, f"element/{element_id}/clear")
                requests.post(clear_url, timeout=10, verify=False)
                return

        # 兜底方案：发送退格键指令
        _clear_with_backspace(wda_url, session_id)

    except ImportError:
        print("Error: requests library required. Install: pip install requests")
    except Exception as e:
        print(f"Error clearing text: {e}")


def _clear_with_backspace(
    wda_url: str = "http://localhost:8100",
    session_id: str | None = None,
    max_backspaces: int = 100,
) -> None:
    """
    通过发送退格键清空文本。

    参数:
        wda_url: WebDriverAgent 地址。
        session_id: 可选的 WDA 会话 ID。
        max_backspaces: 最多发送的退格次数。
    """
    try:
        import requests

        url = _get_wda_session_url(wda_url, session_id, "wda/keys")

        # 多次发送退格字符
        backspace_char = "\u0008"  # 退格字符（Unicode）
        requests.post(
            url,
            json={"value": [backspace_char] * max_backspaces},
            timeout=10,
            verify=False,
        )

    except Exception as e:
        print(f"Error clearing with backspace: {e}")


def send_keys(
    keys: list[str],
    wda_url: str = "http://localhost:8100",
    session_id: str | None = None,
) -> None:
    """
    发送一串按键。

    参数:
        keys: 要发送的按键列表。
        wda_url: WebDriverAgent 地址。
        session_id: 可选的 WDA 会话 ID。

    示例:
        >>> send_keys(["H", "e", "l", "l", "o"])
        >>> send_keys(["\n"])  # 发送回车键
    """
    try:
        import requests

        url = _get_wda_session_url(wda_url, session_id, "wda/keys")

        requests.post(url, json={"value": keys}, timeout=10, verify=False)

    except ImportError:
        print("Error: requests library required. Install: pip install requests")
    except Exception as e:
        print(f"Error sending keys: {e}")


def press_enter(
    wda_url: str = "http://localhost:8100",
    session_id: str | None = None,
    delay: float = 0.5,
) -> None:
    """
    按下 Enter/Return 键。

    参数:
        wda_url: WebDriverAgent 地址。
        session_id: 可选的 WDA 会话 ID。
        delay: 按下后的延迟（秒）。
    """
    send_keys(["\n"], wda_url, session_id)
    time.sleep(delay)


def hide_keyboard(
    wda_url: str = "http://localhost:8100",
    session_id: str | None = None,
) -> None:
    """
    隐藏屏幕键盘。

    参数:
        wda_url: WebDriverAgent 地址。
        session_id: 可选的 WDA 会话 ID。
    """
    try:
        import requests

        url = f"{wda_url.rstrip('/')}/wda/keyboard/dismiss"

        requests.post(url, timeout=10, verify=False)

    except ImportError:
        print("Error: requests library required. Install: pip install requests")
    except Exception as e:
        print(f"Error hiding keyboard: {e}")


def is_keyboard_shown(
    wda_url: str = "http://localhost:8100",
    session_id: str | None = None,
) -> bool:
    """
    检查屏幕键盘是否显示。

    参数:
        wda_url: WebDriverAgent 地址。
        session_id: 可选的 WDA 会话 ID。

    返回:
        键盘显示返回 True，否则返回 False。
    """
    try:
        import requests

        url = _get_wda_session_url(wda_url, session_id, "wda/keyboard/shown")

        response = requests.get(url, timeout=5, verify=False)

        if response.status_code == 200:
            data = response.json()
            return data.get("value", False)

    except ImportError:
        print("Error: requests library required. Install: pip install requests")
    except Exception:
        pass

    return False


def set_pasteboard(
    text: str,
    wda_url: str = "http://localhost:8100",
) -> None:
    """
    设置设备剪贴板内容。

    参数:
        text: 要设置到剪贴板的文本。
        wda_url: WebDriverAgent 地址。

    说明:
        适合输入大量文本。
        设置剪贴板后可模拟粘贴手势。
    """
    try:
        import requests

        url = f"{wda_url.rstrip('/')}/wda/setPasteboard"

        requests.post(
            url, json={"content": text, "contentType": "plaintext"}, timeout=10, verify=False
        )

    except ImportError:
        print("Error: requests library required. Install: pip install requests")
    except Exception as e:
        print(f"Error setting pasteboard: {e}")


def get_pasteboard(
    wda_url: str = "http://localhost:8100",
) -> str | None:
    """
    获取设备剪贴板内容。

    参数:
        wda_url: WebDriverAgent 地址。

    返回:
        剪贴板内容，失败则返回 None。
    """
    try:
        import requests

        url = f"{wda_url.rstrip('/')}/wda/getPasteboard"

        response = requests.post(url, timeout=10, verify=False)

        if response.status_code == 200:
            data = response.json()
            return data.get("value")

    except ImportError:
        print("Error: requests library required. Install: pip install requests")
    except Exception as e:
        print(f"Error getting pasteboard: {e}")

    return None

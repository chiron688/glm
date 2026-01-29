"""用于 Android 设备文本输入的工具。"""

import base64
import subprocess
from typing import Optional


def type_text(text: str, device_id: str | None = None) -> None:
    """
    使用 ADB Keyboard 在当前焦点输入框中输入文本。

    参数:
        text: 要输入的文本。
        device_id: 可选的 ADB 设备 ID（多设备场景）。

    说明:
        需要在设备上安装 ADB Keyboard。
        参考: https://github.com/nicnocquee/AdbKeyboard
    """
    # 关键步骤：输入文本内容
    adb_prefix = _get_adb_prefix(device_id)
    encoded_text = base64.b64encode(text.encode("utf-8")).decode("utf-8")

    subprocess.run(
        adb_prefix
        + [
            "shell",
            "am",
            "broadcast",
            "-a",
            "ADB_INPUT_B64",
            "--es",
            "msg",
            encoded_text,
        ],
        capture_output=True,
        text=True,
    )


def clear_text(device_id: str | None = None) -> None:
    """
    清空当前焦点输入框中的文本。

    参数:
        device_id: 可选的 ADB 设备 ID（多设备场景）。
    """
    # 关键步骤：清空当前输入框内容
    adb_prefix = _get_adb_prefix(device_id)

    subprocess.run(
        adb_prefix + ["shell", "am", "broadcast", "-a", "ADB_CLEAR_TEXT"],
        capture_output=True,
        text=True,
    )


def detect_and_set_adb_keyboard(device_id: str | None = None) -> str:
    """
    检测当前键盘并在需要时切换到 ADB Keyboard。

    参数:
        device_id: 可选的 ADB 设备 ID（多设备场景）。

    返回:
        原始键盘 IME 标识符，用于后续恢复。
    """
    # 关键步骤：切换到 ADB 键盘输入法
    adb_prefix = _get_adb_prefix(device_id)

    # 获取当前 IME
    result = subprocess.run(
        adb_prefix + ["shell", "settings", "get", "secure", "default_input_method"],
        capture_output=True,
        text=True,
    )
    current_ime = (result.stdout + result.stderr).strip()

    # 若未设置 ADB Keyboard，则切换
    if "com.android.adbkeyboard/.AdbIME" not in current_ime:
        subprocess.run(
            adb_prefix + ["shell", "ime", "set", "com.android.adbkeyboard/.AdbIME"],
            capture_output=True,
            text=True,
        )

    # 预热键盘
    type_text("", device_id)

    return current_ime


def restore_keyboard(ime: str, device_id: str | None = None) -> None:
    """
    恢复原始键盘 IME。

    参数:
        ime: 要恢复的 IME 标识符。
        device_id: 可选的 ADB 设备 ID（多设备场景）。
    """
    # 关键步骤：恢复原输入法
    adb_prefix = _get_adb_prefix(device_id)

    subprocess.run(
        adb_prefix + ["shell", "ime", "set", ime], capture_output=True, text=True
    )


def _get_adb_prefix(device_id: str | None) -> list:
    """获取 ADB 命令前缀（可选设备参数）。"""
    # 关键步骤：获取ADBprefix
    if device_id:
        return ["adb", "-s", device_id]
    return ["adb"]

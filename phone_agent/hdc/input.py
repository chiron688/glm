"""用于 HarmonyOS 设备文本输入的工具。"""

import base64
import subprocess
from typing import Optional

from phone_agent.hdc.connection import _run_hdc_command


def type_text(text: str, device_id: str | None = None) -> None:
    """
    在当前焦点输入框中输入文本。

    参数:
        text: 要输入的文本，支持带换行符的多行文本。
        device_id: 可选的 HDC 设备 ID（多设备场景）。

    说明:
        HarmonyOS 使用: hdc shell uitest uiInput text "文本内容"
        当输入框已聚焦时，该命令无需坐标即可生效。
        对多行文本会按换行拆分，并发送 ENTER 的 keyEvent。
        HarmonyOS 的 ENTER 键码为: 2054
        建议先点击输入框获取焦点，再使用此函数输入。
    """
    hdc_prefix = _get_hdc_prefix(device_id)

    # 通过换行拆分来处理多行文本
    if '\n' in text:
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if line:  # 仅处理非空行
                # 对 shell 特殊字符进行转义
                escaped_line = line.replace('"', '\\"').replace("$", "\\$")

                _run_hdc_command(
                    hdc_prefix + ["shell", "uitest", "uiInput", "text", escaped_line],
                    capture_output=True,
                    text=True,
                )

            # 除最后一行外，每行后发送 ENTER 键事件
            if i < len(lines) - 1:
                try:
                    _run_hdc_command(
                        hdc_prefix + ["shell", "uitest", "uiInput", "keyEvent", "2054"],
                        capture_output=True,
                        text=True,
                    )
                except Exception as e:
                    print(f"[HDC] ENTER keyEvent failed: {e}")
    else:
        # 单行文本 - 原始逻辑
        # 转义 shell 特殊字符（保留引号以保证文本处理正确）
        # 文本会在命令中被引号包裹
        escaped_text = text.replace('"', '\\"').replace("$", "\\$")

        # HarmonyOS uitest uiInput text 命令
        # 格式: hdc shell uitest uiInput text "文本内容"
        _run_hdc_command(
            hdc_prefix + ["shell", "uitest", "uiInput", "text", escaped_text],
            capture_output=True,
            text=True,
        )


def clear_text(device_id: str | None = None) -> None:
    """
    清空当前焦点输入框中的文本。

    参数:
        device_id: 可选的 HDC 设备 ID（多设备场景）。

    说明:
        该方法使用重复的删除键事件来清空文本。
        在 HarmonyOS 上也可使用全选 + 删除以提高效率。
    """
    hdc_prefix = _get_hdc_prefix(device_id)
    # Ctrl+A 全选（Ctrl 键码 2072，A 键码 2017）
    # 然后删除
    _run_hdc_command(
        hdc_prefix + ["shell", "uitest", "uiInput", "keyEvent", "2072", "2017"],
        capture_output=True,
        text=True,
    )
    _run_hdc_command(
        hdc_prefix + ["shell", "uitest", "uiInput", "keyEvent", "2055"],  # 删除键
        capture_output=True,
        text=True,
    )


def detect_and_set_adb_keyboard(device_id: str | None = None) -> str:
    """
    检测当前键盘并在可用时切换到 ADB Keyboard。

    参数:
        device_id: 可选的 HDC 设备 ID（多设备场景）。

    返回:
        原始键盘 IME 标识符，用于后续恢复。

    说明:
        这是一个占位实现。HarmonyOS 可能不支持 ADB Keyboard。
        若有类似工具可用，请在此集成。
    """
    hdc_prefix = _get_hdc_prefix(device_id)

    # 获取当前 IME（若 HarmonyOS 支持）
    try:
        result = _run_hdc_command(
            hdc_prefix + ["shell", "settings", "get", "secure", "default_input_method"],
            capture_output=True,
            text=True,
        )
        current_ime = (result.stdout + result.stderr).strip()

        # 若 HarmonyOS 有 ADB Keyboard 等价物，则切换
        # 目前仅返回当前 IME
        return current_ime
    except Exception:
        return ""


def restore_keyboard(ime: str, device_id: str | None = None) -> None:
    """
    恢复原始键盘 IME。

    参数:
        ime: 要恢复的 IME 标识符。
        device_id: 可选的 HDC 设备 ID（多设备场景）。
    """
    if not ime:
        return

    hdc_prefix = _get_hdc_prefix(device_id)

    try:
        _run_hdc_command(
            hdc_prefix + ["shell", "ime", "set", ime], capture_output=True, text=True
        )
    except Exception:
        pass


def _get_hdc_prefix(device_id: str | None) -> list:
    """获取 HDC 命令前缀（可选设备参数）。"""
    if device_id:
        return ["hdc", "-t", device_id]
    return ["hdc"]

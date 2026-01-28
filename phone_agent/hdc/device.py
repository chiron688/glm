"""用于 HarmonyOS 自动化的设备控制工具。"""

import os
import subprocess
import time
from typing import List, Optional, Tuple

from phone_agent.config.apps_harmonyos import APP_ABILITIES, APP_PACKAGES
from phone_agent.config.timing import TIMING_CONFIG
from phone_agent.hdc.connection import _run_hdc_command
import re

def get_current_app(device_id: str | None = None) -> str:
    """
    获取当前前台应用名称。

    参数:
        device_id: 可选的 HDC 设备 ID（多设备场景）。

    返回:
        若可识别则返回应用名称，否则返回 "System Home"。
    """
    hdc_prefix = _get_hdc_prefix(device_id)

    # 使用 'aa dump -l' 列出运行中的 Ability
    result = _run_hdc_command(
        hdc_prefix + ["shell", "aa", "dump", "-l"],
        capture_output=True,
        text=True,
        encoding="utf-8"
    )
    output = result.stdout
    # print(output)
    if not output:
        raise ValueError("No output from aa dump")

    # 解析任务并找到处于 FOREGROUND 状态的任务
    # 输出格式:
    # Mission ID #139
    # mission name #[#com.kuaishou.hmapp:kwai:EntryAbility]
    # app name [com.kuaishou.hmapp]
    # bundle name [com.kuaishou.hmapp]
    # ability type [PAGE]
    # state #FOREGROUND
    # app state #FOREGROUND

    lines = output.split("\n")
    foreground_bundle = None
    current_bundle = None

    for line in lines:
        # 跟踪当前任务的 bundle 名称
        if "app name [" in line:
            match = re.search(r'\[([^\]]+)\]', line)
            if match:
                current_bundle = match.group(1)

        # 检查该任务是否处于 FOREGROUND 状态
        if "state #FOREGROUND" in line or "state #foreground" in line.lower():
            if current_bundle:
                foreground_bundle = current_bundle
                break  # 已找到前台应用，无需继续

        # 开始新任务时重置 current_bundle
        if "Mission ID" in line:
            current_bundle = None

    # 与已知应用进行匹配
    if foreground_bundle:
        for app_name, package in APP_PACKAGES.items():
            if package == foreground_bundle:
                return app_name
        # 若 bundle 不在已知应用列表中，则返回 bundle 名称
        print(f'Bundle is found but not in our known apps: {foreground_bundle}')
        return foreground_bundle
    print(f'No bundle is found')
    return "System Home"


def get_ui_tree(device_id: str | None = None, timeout: int = 10) -> str | None:
    """
    Dump the current UI hierarchy as XML.

    HarmonyOS UI dump support varies by device; return None when unavailable.
    """
    hdc_prefix = _get_hdc_prefix(device_id)
    try:
        result = _run_hdc_command(
            hdc_prefix + ["shell", "uitest", "dumpLayout"],
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
        )
        if result.returncode != 0:
            return None
        output = (result.stdout or "").strip()
        if not output:
            return None
        # Some devices prepend logs; try to extract JSON payload.
        start = output.find("{")
        end = output.rfind("}")
        if start != -1 and end != -1 and end > start:
            output = output[start : end + 1]
        if not output.startswith("{") and not output.startswith("["):
            return None
        return output
    except Exception:
        return None


def tap(
    x: int, y: int, device_id: str | None = None, delay: float | None = None
) -> None:
    """
    在指定坐标点击。

    参数:
        x: X 坐标。
        y: Y 坐标。
        device_id: 可选的 HDC 设备 ID。
        delay: 点击后的延迟（秒）。为 None 时使用默认配置。
    """
    if delay is None:
        delay = TIMING_CONFIG.device.default_tap_delay

    hdc_prefix = _get_hdc_prefix(device_id)

    # HarmonyOS 使用 uitest uiInput click
    _run_hdc_command(
        hdc_prefix + ["shell", "uitest", "uiInput", "click", str(x), str(y)],
        capture_output=True
    )
    time.sleep(delay)


def double_tap(
    x: int, y: int, device_id: str | None = None, delay: float | None = None
) -> None:
    """
    在指定坐标双击。

    参数:
        x: X 坐标。
        y: Y 坐标。
        device_id: 可选的 HDC 设备 ID。
        delay: 双击后的延迟（秒）。为 None 时使用默认配置。
    """
    if delay is None:
        delay = TIMING_CONFIG.device.default_double_tap_delay

    hdc_prefix = _get_hdc_prefix(device_id)

    # HarmonyOS 使用 uitest uiInput doubleClick
    _run_hdc_command(
        hdc_prefix + ["shell", "uitest", "uiInput", "doubleClick", str(x), str(y)],
        capture_output=True
    )
    time.sleep(delay)


def long_press(
    x: int,
    y: int,
    duration_ms: int = 3000,
    device_id: str | None = None,
    delay: float | None = None,
) -> None:
    """
    在指定坐标长按。

    参数:
        x: X 坐标。
        y: Y 坐标。
        duration_ms: 长按持续时间（毫秒，注意：HarmonyOS 的 longClick 可能不支持时长）。
        device_id: 可选的 HDC 设备 ID。
        delay: 长按后的延迟（秒）。为 None 时使用默认配置。
    """
    if delay is None:
        delay = TIMING_CONFIG.device.default_long_press_delay

    hdc_prefix = _get_hdc_prefix(device_id)

    # HarmonyOS 使用 uitest uiInput longClick
    # 注意：longClick 可能为固定时长，duration_ms 参数可能不被支持
    _run_hdc_command(
        hdc_prefix + ["shell", "uitest", "uiInput", "longClick", str(x), str(y)],
        capture_output=True,
    )
    time.sleep(delay)


def swipe(
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    duration_ms: int | None = None,
    device_id: str | None = None,
    delay: float | None = None,
) -> None:
    """
    从起点滑动到终点。

    参数:
        start_x: 起点 X 坐标。
        start_y: 起点 Y 坐标。
        end_x: 终点 X 坐标。
        end_y: 终点 Y 坐标。
        duration_ms: 滑动持续时间（毫秒，None 时自动计算）。
        device_id: 可选的 HDC 设备 ID。
        delay: 滑动后的延迟（秒）。为 None 时使用默认配置。
    """
    if delay is None:
        delay = TIMING_CONFIG.device.default_swipe_delay

    hdc_prefix = _get_hdc_prefix(device_id)

    if duration_ms is None:
        # 根据距离计算持续时间
        dist_sq = (start_x - end_x) ** 2 + (start_y - end_y) ** 2
        duration_ms = int(dist_sq / 1000)
        duration_ms = max(500, min(duration_ms, 1000))  # 限制在 500-1000ms

    # HarmonyOS 使用 uitest uiInput swipe
    # 格式: swipe startX startY endX endY duration
    _run_hdc_command(
        hdc_prefix
        + [
            "shell",
            "uitest",
            "uiInput",
            "swipe",
            str(start_x),
            str(start_y),
            str(end_x),
            str(end_y),
            str(duration_ms),
        ],
        capture_output=True,
    )
    time.sleep(delay)


def back(device_id: str | None = None, delay: float | None = None) -> None:
    """
    按下返回键。

    参数:
        device_id: 可选的 HDC 设备 ID。
        delay: 返回后的延迟（秒）。为 None 时使用默认配置。
    """
    if delay is None:
        delay = TIMING_CONFIG.device.default_back_delay

    hdc_prefix = _get_hdc_prefix(device_id)

    # HarmonyOS 使用 uitest uiInput keyEvent Back
    _run_hdc_command(
        hdc_prefix + ["shell", "uitest", "uiInput", "keyEvent", "Back"],
        capture_output=True
    )
    time.sleep(delay)


def home(device_id: str | None = None, delay: float | None = None) -> None:
    """
    按下 Home 键。

    参数:
        device_id: 可选的 HDC 设备 ID。
        delay: 按下后的延迟（秒）。为 None 时使用默认配置。
    """
    if delay is None:
        delay = TIMING_CONFIG.device.default_home_delay

    hdc_prefix = _get_hdc_prefix(device_id)

    # HarmonyOS 使用 uitest uiInput keyEvent Home
    _run_hdc_command(
        hdc_prefix + ["shell", "uitest", "uiInput", "keyEvent", "Home"],
        capture_output=True
    )
    time.sleep(delay)


def launch_app(
    app_name: str, device_id: str | None = None, delay: float | None = None
) -> bool:
    """
    根据应用名称启动应用。

    参数:
        app_name: 应用名称（必须存在于 APP_PACKAGES）。
        device_id: 可选的 HDC 设备 ID。
        delay: 启动后的延迟（秒）。为 None 时使用默认配置。

    返回:
        启动成功返回 True，未找到应用返回 False。
    """
    if delay is None:
        delay = TIMING_CONFIG.device.default_launch_delay

    if app_name not in APP_PACKAGES:
        print(f"[HDC] App '{app_name}' not found in HarmonyOS app list")
        print(f"[HDC] Available apps: {', '.join(sorted(APP_PACKAGES.keys())[:10])}...")
        return False

    hdc_prefix = _get_hdc_prefix(device_id)
    bundle = APP_PACKAGES[app_name]

    # 获取该 bundle 对应的 Ability 名称
    # 若 APP_ABILITIES 未指定，则默认使用 "EntryAbility"
    ability = APP_ABILITIES.get(bundle, "EntryAbility")

    # HarmonyOS 使用 'aa start' 命令启动应用
    # 格式: aa start -b {bundle} -a {ability}
    _run_hdc_command(
        hdc_prefix
        + [
            "shell",
            "aa",
            "start",
            "-b",
            bundle,
            "-a",
            ability,
        ],
        capture_output=True,
    )
    time.sleep(delay)
    return True


def _get_hdc_prefix(device_id: str | None) -> list:
    """获取 HDC 命令前缀（可选设备参数）。"""
    if device_id:
        return ["hdc", "-t", device_id]
    return ["hdc"]

if __name__ == "__main__":
    print(get_current_app())

"""用于 Android 自动化的设备控制工具。"""

import os
import subprocess
import time
from typing import List, Optional, Tuple

from phone_agent.config.apps import APP_PACKAGES
from phone_agent.config.timing import TIMING_CONFIG


def get_current_app(device_id: str | None = None) -> str:
    """
    获取当前前台应用名称。

    参数:
        device_id: 可选的 ADB 设备 ID（多设备场景）。

    返回:
        若可识别则返回应用名称，否则返回 "System Home"。
    """
    # 关键步骤：获取当前前台应用包名
    adb_prefix = _get_adb_prefix(device_id)

    result = subprocess.run(
        adb_prefix + ["shell", "dumpsys", "window"], capture_output=True, text=True, encoding="utf-8"
    )
    output = result.stdout
    if not output:
        raise ValueError("No output from dumpsys window")

    # 解析窗口焦点信息
    for line in output.split("\n"):
        if "mCurrentFocus" in line or "mFocusedApp" in line:
            for app_name, package in APP_PACKAGES.items():
                if package in line:
                    return app_name

    return "System Home"


def get_ui_tree(device_id: str | None = None, timeout: int = 10) -> str | None:
    """
    Dump the current UI hierarchy as XML using uiautomator.

    Returns None if the dump fails or is unavailable.
    """
    # 关键步骤：获取uitree
    adb_prefix = _get_adb_prefix(device_id)
    remote_path = "/sdcard/uidump.xml"
    try:
        subprocess.run(
            adb_prefix + ["shell", "uiautomator", "dump", remote_path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        result = subprocess.run(
            adb_prefix + ["shell", "cat", remote_path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            return None
        xml = result.stdout.strip()
        if "<hierarchy" not in xml:
            return None
        return xml
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
        device_id: 可选的 ADB 设备 ID。
        delay: 点击后的延迟（秒）。为 None 时使用默认配置。
    """
    # 关键步骤：点击ADB 设备控制相关逻辑
    if delay is None:
        delay = TIMING_CONFIG.device.default_tap_delay

    adb_prefix = _get_adb_prefix(device_id)

    subprocess.run(
        adb_prefix + ["shell", "input", "tap", str(x), str(y)], capture_output=True
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
        device_id: 可选的 ADB 设备 ID。
        delay: 双击后的延迟（秒）。为 None 时使用默认配置。
    """
    # 关键步骤：双击tap
    if delay is None:
        delay = TIMING_CONFIG.device.default_double_tap_delay

    adb_prefix = _get_adb_prefix(device_id)

    subprocess.run(
        adb_prefix + ["shell", "input", "tap", str(x), str(y)], capture_output=True
    )
    time.sleep(TIMING_CONFIG.device.double_tap_interval)
    subprocess.run(
        adb_prefix + ["shell", "input", "tap", str(x), str(y)], capture_output=True
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
        duration_ms: 长按持续时间（毫秒）。
        device_id: 可选的 ADB 设备 ID。
        delay: 长按后的延迟（秒）。为 None 时使用默认配置。
    """
    # 关键步骤：长按press
    if delay is None:
        delay = TIMING_CONFIG.device.default_long_press_delay

    adb_prefix = _get_adb_prefix(device_id)

    subprocess.run(
        adb_prefix
        + ["shell", "input", "swipe", str(x), str(y), str(x), str(y), str(duration_ms)],
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
        device_id: 可选的 ADB 设备 ID。
        delay: 滑动后的延迟（秒）。为 None 时使用默认配置。
    """
    # 关键步骤：滑动ADB 设备控制相关逻辑
    if delay is None:
        delay = TIMING_CONFIG.device.default_swipe_delay

    adb_prefix = _get_adb_prefix(device_id)

    if duration_ms is None:
        # 根据距离计算持续时间
        dist_sq = (start_x - end_x) ** 2 + (start_y - end_y) ** 2
        duration_ms = int(dist_sq / 1000)
        duration_ms = max(1000, min(duration_ms, 2000))  # 限制在 1000-2000ms

    subprocess.run(
        adb_prefix
        + [
            "shell",
            "input",
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
        device_id: 可选的 ADB 设备 ID。
        delay: 返回后的延迟（秒）。为 None 时使用默认配置。
    """
    # 关键步骤：返回ADB 设备控制相关逻辑
    if delay is None:
        delay = TIMING_CONFIG.device.default_back_delay

    adb_prefix = _get_adb_prefix(device_id)

    subprocess.run(
        adb_prefix + ["shell", "input", "keyevent", "4"], capture_output=True
    )
    time.sleep(delay)


def home(device_id: str | None = None, delay: float | None = None) -> None:
    """
    按下 Home 键。

    参数:
        device_id: 可选的 ADB 设备 ID。
        delay: 按下后的延迟（秒）。为 None 时使用默认配置。
    """
    # 关键步骤：主页ADB 设备控制相关逻辑
    if delay is None:
        delay = TIMING_CONFIG.device.default_home_delay

    adb_prefix = _get_adb_prefix(device_id)

    subprocess.run(
        adb_prefix + ["shell", "input", "keyevent", "KEYCODE_HOME"], capture_output=True
    )
    time.sleep(delay)


def launch_app(
    app_name: str, device_id: str | None = None, delay: float | None = None
) -> bool:
    """
    根据应用名称启动应用。

    参数:
        app_name: 应用名称（必须存在于 APP_PACKAGES）。
        device_id: 可选的 ADB 设备 ID。
        delay: 启动后的延迟（秒）。为 None 时使用默认配置。

    返回:
        启动成功返回 True，未找到应用返回 False。
    """
    # 关键步骤：启动指定应用
    if delay is None:
        delay = TIMING_CONFIG.device.default_launch_delay

    if app_name not in APP_PACKAGES:
        return False

    adb_prefix = _get_adb_prefix(device_id)
    package = APP_PACKAGES[app_name]

    subprocess.run(
        adb_prefix
        + [
            "shell",
            "monkey",
            "-p",
            package,
            "-c",
            "android.intent.category.LAUNCHER",
            "1",
        ],
        capture_output=True,
    )
    time.sleep(delay)
    return True


def _get_adb_prefix(device_id: str | None) -> list:
    """获取 ADB 命令前缀（可选设备参数）。"""
    # 关键步骤：获取ADBprefix
    if device_id:
        return ["adb", "-s", device_id]
    return ["adb"]

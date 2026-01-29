"""用于捕获 HarmonyOS 设备屏幕的截图工具。"""

import base64
import os
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from io import BytesIO
from typing import Tuple

from PIL import Image
from phone_agent.hdc.connection import _run_hdc_command


@dataclass
class Screenshot:
    """表示一次捕获的截图。"""

    base64_data: str
    width: int
    height: int
    is_sensitive: bool = False


def get_screenshot(device_id: str | None = None, timeout: int = 10) -> Screenshot:
    """
    从连接的 HarmonyOS 设备获取截图。

    参数:
        device_id: 可选的 HDC 设备 ID（多设备场景）。
        timeout: 截图操作的超时时间（秒）。

    返回:
        包含 base64 数据和尺寸的 Screenshot 对象。

    说明:
        若截图失败（例如支付页面等敏感界面），
        将返回黑色占位图，并设置 is_sensitive=True。
    """
    # 关键步骤：获取屏幕截图并编码为 base64
    temp_path = os.path.join(tempfile.gettempdir(), f"screenshot_{uuid.uuid4()}.png")
    hdc_prefix = _get_hdc_prefix(device_id)

    try:
        # 执行截图命令
        # HarmonyOS HDC 仅支持 JPEG 格式
        remote_path = "/data/local/tmp/tmp_screenshot.jpeg"

        # 方法 1：hdc shell screenshot（较新的 HarmonyOS 版本）
        result = _run_hdc_command(
            hdc_prefix + ["shell", "screenshot", remote_path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        # 检查截图是否失败（敏感界面）
        output = result.stdout + result.stderr
        if "fail" in output.lower() or "error" in output.lower() or "not found" in output.lower():
            # 方法 2：snapshot_display（旧版本或不同设备）
            result = _run_hdc_command(
                hdc_prefix + ["shell", "snapshot_display", "-f", remote_path],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            output = result.stdout + result.stderr
            if "fail" in output.lower() or "error" in output.lower():
                return _create_fallback_screenshot(is_sensitive=True)

        # 将截图拉取到本地临时路径
        # 注意：远端文件为 JPEG，但 PIL 可按内容识别格式
        _run_hdc_command(
            hdc_prefix + ["file", "recv", remote_path, temp_path],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if not os.path.exists(temp_path):
            return _create_fallback_screenshot(is_sensitive=False)

        # 读取 JPEG 并转换为 PNG，供模型推理使用
        # PIL 会根据文件内容自动识别格式
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

    except Exception as e:
        print(f"Screenshot error: {e}")
        return _create_fallback_screenshot(is_sensitive=False)


def _get_hdc_prefix(device_id: str | None) -> list:
    """获取 HDC 命令前缀（可选设备参数）。"""
    # 关键步骤：获取HDCprefix
    if device_id:
        return ["hdc", "-t", device_id]
    return ["hdc"]


def _create_fallback_screenshot(is_sensitive: bool) -> Screenshot:
    """截图失败时创建黑色占位图。"""
    # 关键步骤：处理fallback截图
    default_width, default_height = 1080, 2400

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

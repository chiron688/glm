"""Utility helpers for skills."""

from __future__ import annotations

import base64
import random
import re
import time
from copy import deepcopy
from io import BytesIO
from typing import Any

from PIL import Image

_TEMPLATE_RE = re.compile(r"\{\{(\w+)\}\}")
_TEMPLATE_LIST_RE = re.compile(r"^\{\{(\w+)\}\}$")


def render_string(value: str, variables: dict[str, Any]) -> str:
    """渲染字符串模板，将 {{var}} 替换为变量值。"""
    # 关键步骤：替换模板变量（通用工具）
    def replacer(match: re.Match[str]) -> str:
        """将单个模板占位符替换为变量值。"""
        # 关键步骤：输出占位符对应值（通用工具）
        key = match.group(1)
        if key in variables:
            return str(variables[key])
        return match.group(0)

    return _TEMPLATE_RE.sub(replacer, value)


def render_templates(obj: Any, variables: dict[str, Any]) -> Any:
    """用于通用工具，渲染模板，涉及模板渲染。"""
    # 关键步骤：渲染模板（通用工具）
    if isinstance(obj, str):
        match = _TEMPLATE_LIST_RE.match(obj.strip())
        if match:
            key = match.group(1)
            if key in variables and isinstance(variables[key], list):
                return variables[key]
        return render_string(obj, variables)
    if isinstance(obj, list):
        return [render_templates(item, variables) for item in obj]
    if isinstance(obj, dict):
        return {key: render_templates(value, variables) for key, value in obj.items()}
    return obj


def deep_copy(obj: Any) -> Any:
    """对对象执行深拷贝，避免引用共享。"""
    # 关键步骤：深拷贝对象（通用工具）
    return deepcopy(obj)


def decode_image_from_base64(base64_data: str) -> Image.Image:
    """从 base64 解码图像并返回 PIL Image。"""
    # 关键步骤：解码 base64 图像（通用工具）
    raw = base64.b64decode(base64_data)
    return Image.open(BytesIO(raw))


def compute_ahash(image: Image.Image, hash_size: int = 8) -> str:
    """计算图像的平均哈希（aHash）用于快速相似度比较。"""
    # 关键步骤：生成 aHash 指纹（通用工具）
    grayscale = image.convert("L").resize((hash_size, hash_size))
    pixels = list(grayscale.getdata())
    avg = sum(pixels) / len(pixels)
    bits = ["1" if px >= avg else "0" for px in pixels]
    hex_str = "%0*x" % (hash_size * hash_size // 4, int("".join(bits), 2))
    return hex_str


def hamming_distance(hash_a: str, hash_b: str) -> int:
    """计算两个哈希值的汉明距离。"""
    # 关键步骤：计算哈希差异（通用工具）
    if len(hash_a) != len(hash_b):
        raise ValueError("Hash length mismatch")
    value_a = int(hash_a, 16)
    value_b = int(hash_b, 16)
    return (value_a ^ value_b).bit_count()


def sleep_with_backoff(
    attempt: int,
    base_ms: int,
    multiplier: float,
    max_ms: int,
    jitter_ms: int,
) -> None:
    """按指数退避 + 随机抖动策略等待。"""
    # 关键步骤：退避等待（通用工具）
    delay = min(int(base_ms * (multiplier ** max(0, attempt - 1))), max_ms)
    if jitter_ms > 0:
        delay += random.randint(0, jitter_ms)
    time.sleep(delay / 1000.0)

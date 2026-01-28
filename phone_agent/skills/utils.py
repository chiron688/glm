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
    def replacer(match: re.Match[str]) -> str:
        key = match.group(1)
        if key in variables:
            return str(variables[key])
        return match.group(0)

    return _TEMPLATE_RE.sub(replacer, value)


def render_templates(obj: Any, variables: dict[str, Any]) -> Any:
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
    return deepcopy(obj)


def decode_image_from_base64(base64_data: str) -> Image.Image:
    raw = base64.b64decode(base64_data)
    return Image.open(BytesIO(raw))


def compute_ahash(image: Image.Image, hash_size: int = 8) -> str:
    grayscale = image.convert("L").resize((hash_size, hash_size))
    pixels = list(grayscale.getdata())
    avg = sum(pixels) / len(pixels)
    bits = ["1" if px >= avg else "0" for px in pixels]
    hex_str = "%0*x" % (hash_size * hash_size // 4, int("".join(bits), 2))
    return hex_str


def hamming_distance(hash_a: str, hash_b: str) -> int:
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
    delay = min(int(base_ms * (multiplier ** max(0, attempt - 1))), max_ms)
    if jitter_ms > 0:
        delay += random.randint(0, jitter_ms)
    time.sleep(delay / 1000.0)

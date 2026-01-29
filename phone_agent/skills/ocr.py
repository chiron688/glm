"""OCR provider interface for skill selectors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from PIL import Image


@dataclass(frozen=True)
class OcrResult:
    text: str
    bounds: tuple[int, int, int, int]
    confidence: float | None = None


class OcrProvider(Protocol):
    def extract(self, image: Image.Image) -> list[OcrResult]:
        """用于OCR 识别，提取文本与边界框。"""
        # 关键步骤：提取文本与边界框（OCR 识别）
        ...


class NullOcrProvider:
    def extract(self, image: Image.Image) -> list[OcrResult]:
        """用于OCR 识别，提取文本与边界框。"""
        # 关键步骤：提取文本与边界框（OCR 识别）
        _ = image
        return []


class TesseractOcrProvider:
    def __init__(self, lang: str = "eng", config: str = "") -> None:
        """初始化TesseractOcrProvider，准备OCR 识别所需的依赖、状态与默认配置。"""
        # 关键步骤：初始化（OCR 识别）
        self.lang = lang
        self.config = config

    def extract(self, image: Image.Image) -> list[OcrResult]:
        """用于OCR 识别，提取文本与边界框。"""
        # 关键步骤：提取文本与边界框（OCR 识别）
        try:
            import pytesseract
        except ImportError as exc:
            raise RuntimeError("pytesseract is required for TesseractOcrProvider") from exc

        data = pytesseract.image_to_data(
            image,
            lang=self.lang,
            config=self.config,
            output_type=pytesseract.Output.DICT,
        )
        results: list[OcrResult] = []
        n = len(data.get("text", []))
        for i in range(n):
            text = (data.get("text") or [""])[i]
            if not text or text.strip() == "":
                continue
            left = int((data.get("left") or [0])[i])
            top = int((data.get("top") or [0])[i])
            width = int((data.get("width") or [0])[i])
            height = int((data.get("height") or [0])[i])
            conf_raw = (data.get("conf") or ["-1"])[i]
            try:
                conf = float(conf_raw) / 100.0
            except (ValueError, TypeError):
                conf = None
            results.append(
                OcrResult(
                    text=text,
                    bounds=(left, top, left + width, top + height),
                    confidence=conf,
                )
            )
        return results


class PaddleOcrProvider:
    def __init__(
        self,
        lang: str = "en",
        use_angle_cls: bool = True,
        force_v5: bool = False,
        **kwargs: Any,
    ) -> None:
        """初始化PaddleOcrProvider，准备OCR 识别所需的依赖、状态与默认配置。"""
        # 关键步骤：初始化（OCR 识别）
        try:
            from paddleocr import PaddleOCR
        except ImportError as exc:
            raise RuntimeError(
                "paddleocr is required for PaddleOcrProvider"
            ) from exc
        import inspect
        self.lang = lang
        self.use_angle_cls = use_angle_cls
        init_kwargs: dict[str, Any] = {"use_angle_cls": use_angle_cls, "lang": lang}
        init_kwargs.update(kwargs)

        if force_v5:
            params = inspect.signature(PaddleOCR.__init__).parameters
            supported = False
            if "ocr_version" in params and "ocr_version" not in init_kwargs:
                init_kwargs["ocr_version"] = "PP-OCRv5"
                supported = True
            if any(
                key in init_kwargs
                for key in ("det_model_dir", "rec_model_dir", "cls_model_dir")
            ):
                supported = True
            if not supported:
                raise RuntimeError(
                    "PaddleOCR v5 not configured. Update paddleocr to v5+ or provide "
                    "det_model_dir/rec_model_dir/cls_model_dir."
                )

        self._ocr = PaddleOCR(**init_kwargs)

    def extract(self, image: Image.Image) -> list[OcrResult]:
        """用于OCR 识别，提取文本与边界框。"""
        # 关键步骤：提取文本与边界框（OCR 识别）
        try:
            import numpy as np
        except ImportError as exc:
            raise RuntimeError("numpy is required for PaddleOcrProvider") from exc

        rgb = image.convert("RGB")
        img = np.array(rgb)
        # PaddleOCR expects BGR format in many cases
        img = img[:, :, ::-1]

        results: list[OcrResult] = []
        ocr_result = self._ocr.ocr(img, cls=self.use_angle_cls)
        if not ocr_result:
            return results

        for line in ocr_result:
            if not line:
                continue
            for item in line:
                if not item or len(item) < 2:
                    continue
                box = item[0]
                text = item[1][0] if isinstance(item[1], (list, tuple)) else ""
                conf = item[1][1] if isinstance(item[1], (list, tuple)) and len(item[1]) > 1 else None
                if not text or text.strip() == "":
                    continue
                xs = [int(point[0]) for point in box]
                ys = [int(point[1]) for point in box]
                bounds = (min(xs), min(ys), max(xs), max(ys))
                results.append(OcrResult(text=text, bounds=bounds, confidence=conf))
        return results


class GemmaOcrProvider:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model_name: str = "google/gemma-3n-E2B-it-litert-lm",
        max_tokens: int = 1024,
        temperature: float = 0.0,
        extra_body: dict[str, Any] | None = None,
        prompt: str | None = None,
    ) -> None:
        """初始化GemmaOcrProvider，准备OCR 识别所需的依赖、状态与默认配置。"""
        # 关键步骤：初始化（OCR 识别）
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("openai is required for GemmaOcrProvider") from exc

        self.base_url = base_url
        self.api_key = api_key
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.extra_body = extra_body or {}
        self.prompt = prompt or (
            "You are an OCR engine. Extract all visible text and bounding boxes. "
            "Return JSON only in the format: {\"items\": [{\"text\": \"...\", \"bounds\": [l,t,r,b]}]} "
            "Bounds are pixel coordinates relative to the input image."
        )
        self.client = OpenAI(base_url=base_url, api_key=api_key)

    def extract(self, image: Image.Image) -> list[OcrResult]:
        """用于OCR 识别，提取文本与边界框。"""
        # 关键步骤：提取文本与边界框（OCR 识别）
        import base64
        import json
        from io import BytesIO

        from phone_agent.model.client import MessageBuilder

        buffered = BytesIO()
        image.save(buffered, format="PNG")
        base64_data = base64.b64encode(buffered.getvalue()).decode("utf-8")

        user_text = (
            f"{self.prompt}\\n"
            f"Image size: {image.width}x{image.height}"
        )
        messages = [
            MessageBuilder.create_system_message("You are a precise OCR extractor."),
            MessageBuilder.create_user_message(text=user_text, image_base64=base64_data),
        ]

        response = self.client.chat.completions.create(
            messages=messages,
            model=self.model_name,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            extra_body=self.extra_body,
        )
        content = ""
        if response and response.choices:
            message = response.choices[0].message
            if isinstance(message.content, list):
                content = "".join(
                    item.get("text", "") for item in message.content if isinstance(item, dict)
                )
            else:
                content = message.content or ""

        try:
            data = json.loads(_extract_json(content))
        except Exception:
            return []

        items = data.get("items", [])
        results: list[OcrResult] = []
        for item in items:
            text = str(item.get("text", "")).strip()
            bounds = item.get("bounds")
            if not text or not isinstance(bounds, list) or len(bounds) != 4:
                continue
            try:
                left, top, right, bottom = map(int, bounds)
            except (TypeError, ValueError):
                continue
            results.append(OcrResult(text=text, bounds=(left, top, right, bottom)))
        return results


def build_ocr_provider(
    provider: str,
    **kwargs: Any,
) -> OcrProvider:
    """根据名称构建 OCR 提供器（Paddle/Gemma）。"""
    # 关键步骤：选择并实例化 OCR 提供器
    name = (provider or "").strip().lower()
    if name in ("paddle", "paddleocr"):
        return PaddleOcrProvider(**kwargs)
    if name in ("gemma", "google-gemma"):
        return GemmaOcrProvider(**kwargs)
    raise ValueError(f"Unsupported OCR provider: {provider}")


def _extract_json(text: str) -> str:
    """从文本中提取 JSON 片段。"""
    # 关键步骤：截取 JSON 内容（OCR 识别）
    text = (text or "").strip()
    if text.startswith("{") and text.endswith("}"):
        return text
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return "{}"
    return text[start : end + 1]

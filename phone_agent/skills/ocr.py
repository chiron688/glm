"""OCR provider interface for skill selectors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from PIL import Image


@dataclass(frozen=True)
class OcrResult:
    text: str
    bounds: tuple[int, int, int, int]
    confidence: float | None = None


class OcrProvider(Protocol):
    def extract(self, image: Image.Image) -> list[OcrResult]:
        ...


class NullOcrProvider:
    def extract(self, image: Image.Image) -> list[OcrResult]:
        _ = image
        return []


class TesseractOcrProvider:
    def __init__(self, lang: str = "eng", config: str = "") -> None:
        self.lang = lang
        self.config = config

    def extract(self, image: Image.Image) -> list[OcrResult]:
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

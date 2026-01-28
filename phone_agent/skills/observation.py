"""Observation capture for skills."""

from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from phone_agent.device_factory import get_device_factory
from phone_agent.skills.ocr import OcrProvider
from phone_agent.skills.selector import UINode, extract_texts, parse_ui_dump
from phone_agent.skills.utils import compute_ahash, decode_image_from_base64


@dataclass
class Observation:
    screenshot: Any
    app_name: str
    device_id: str | None
    ui_tree: str | None
    ui_nodes: list[Any]
    ui_texts: list[str]
    screen_hash: str | None
    timestamp: float

    @property
    def width(self) -> int:
        return self.screenshot.width

    @property
    def height(self) -> int:
        return self.screenshot.height


@dataclass
class StoredScreenshot:
    base64_data: str
    width: int
    height: int
    is_sensitive: bool = False


class ObservationProvider:
    def __init__(
        self,
        device_id: str | None = None,
        include_ui_tree: bool = True,
        include_screen_hash: bool = True,
        ocr_provider: OcrProvider | None = None,
    ) -> None:
        self.device_id = device_id
        self.include_ui_tree = include_ui_tree
        self.include_screen_hash = include_screen_hash
        self.ocr_provider = ocr_provider
        self.device_factory = get_device_factory()

    def capture(self) -> Observation:
        screenshot = self.device_factory.get_screenshot(self.device_id)
        app_name = self.device_factory.get_current_app(self.device_id)
        ui_tree = None
        ui_nodes: list[Any] = []
        ui_texts: list[str] = []

        if self.include_ui_tree:
            try:
                ui_tree = self.device_factory.get_ui_tree(self.device_id)
            except Exception:
                ui_tree = None
        if ui_tree:
            ui_nodes = parse_ui_dump(ui_tree)
            ui_texts = extract_texts(ui_nodes)

        if self.ocr_provider is not None:
            try:
                image = decode_image_from_base64(screenshot.base64_data)
                ocr_results = self.ocr_provider.extract(image)
                for result in ocr_results:
                    ui_nodes.append(
                        UINode(
                            text=result.text,
                            resource_id="",
                            content_desc="",
                            class_name="ocr",
                            clickable=False,
                            bounds=result.bounds,
                        )
                    )
                ui_texts = extract_texts(ui_nodes)
            except Exception:
                pass

        screen_hash = None
        if self.include_screen_hash:
            try:
                image = decode_image_from_base64(screenshot.base64_data)
                screen_hash = compute_ahash(image)
            except Exception:
                screen_hash = None

        return Observation(
            screenshot=screenshot,
            app_name=app_name,
            device_id=self.device_id,
            ui_tree=ui_tree,
            ui_nodes=ui_nodes,
            ui_texts=ui_texts,
            screen_hash=screen_hash,
            timestamp=time.time(),
        )


class RecordingObservationProvider:
    def __init__(self, inner: ObservationProvider, record_dir: str | Path) -> None:
        self.inner = inner
        self.record_dir = Path(record_dir)
        self.record_dir.mkdir(parents=True, exist_ok=True)
        self.index = 0

    def capture(self) -> Observation:
        observation = self.inner.capture()
        self.index += 1
        self._save_observation(observation, self.index)
        return observation

    def _save_observation(self, observation: Observation, index: int) -> None:
        screenshot_file = self.record_dir / f"obs_{index:04d}.png"
        ui_tree_file = self.record_dir / f"obs_{index:04d}.xml"
        meta_file = self.record_dir / f"obs_{index:04d}.json"

        try:
            image = decode_image_from_base64(observation.screenshot.base64_data)
            image.save(screenshot_file)
        except Exception:
            screenshot_file = Path()

        if observation.ui_tree:
            try:
                ui_tree_file.write_text(observation.ui_tree, encoding="utf-8")
            except Exception:
                ui_tree_file = Path()
        else:
            ui_tree_file = Path()

        meta = {
            "app_name": observation.app_name,
            "device_id": observation.device_id,
            "timestamp": observation.timestamp,
            "screen_hash": observation.screen_hash,
            "width": observation.width,
            "height": observation.height,
            "is_sensitive": getattr(observation.screenshot, "is_sensitive", False),
            "screenshot_file": str(screenshot_file.name) if screenshot_file else None,
            "ui_tree_file": str(ui_tree_file.name) if ui_tree_file else None,
        }
        meta_file.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


class PlaybackObservationProvider:
    def __init__(self, playback_dir: str | Path) -> None:
        self.playback_dir = Path(playback_dir)
        self.records = sorted(self.playback_dir.glob("obs_*.json"))
        self.index = 0
        if not self.records:
            raise ValueError(f"No recorded observations found in {self.playback_dir}")

    def capture(self) -> Observation:
        if self.index >= len(self.records):
            raise IndexError("Playback observations exhausted")
        record_path = self.records[self.index]
        self.index += 1
        meta = json.loads(record_path.read_text(encoding="utf-8"))
        screenshot_file = meta.get("screenshot_file")
        ui_tree_file = meta.get("ui_tree_file")

        base64_data = ""
        if screenshot_file:
            image_path = self.playback_dir / screenshot_file
            if image_path.exists():
                raw = image_path.read_bytes()
                base64_data = base64.b64encode(raw).decode("utf-8")

        width = int(meta.get("width", 0))
        height = int(meta.get("height", 0))
        screenshot = StoredScreenshot(
            base64_data=base64_data,
            width=width,
            height=height,
            is_sensitive=bool(meta.get("is_sensitive", False)),
        )

        ui_tree = None
        if ui_tree_file:
            ui_path = self.playback_dir / ui_tree_file
            if ui_path.exists():
                ui_tree = ui_path.read_text(encoding="utf-8")

        ui_nodes: list[Any] = []
        ui_texts: list[str] = []
        if ui_tree:
            ui_nodes = parse_ui_dump(ui_tree)
            ui_texts = extract_texts(ui_nodes)

        return Observation(
            screenshot=screenshot,
            app_name=meta.get("app_name", ""),
            device_id=meta.get("device_id"),
            ui_tree=ui_tree,
            ui_nodes=ui_nodes,
            ui_texts=ui_texts,
            screen_hash=meta.get("screen_hash"),
            timestamp=float(meta.get("timestamp", time.time())),
        )

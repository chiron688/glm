"""Observation capture for iOS skills (WDA-based)."""

from __future__ import annotations

import time
from typing import Any

from phone_agent.skills.observation import Observation
from phone_agent.skills.ocr import OcrProvider
from phone_agent.skills.selector import UINode, extract_texts
from phone_agent.skills.utils import compute_ahash, decode_image_from_base64
from phone_agent.xctest import get_current_app, get_screenshot


class IOSObservationProvider:
    def __init__(
        self,
        wda_url: str = "http://localhost:8100",
        session_id: str | None = None,
        device_id: str | None = None,
        include_screen_hash: bool = True,
        ocr_provider: OcrProvider | None = None,
    ) -> None:
        self.wda_url = wda_url
        self.session_id = session_id
        self.device_id = device_id
        self.include_screen_hash = include_screen_hash
        self.ocr_provider = ocr_provider

    def capture(self) -> Observation:
        screenshot = get_screenshot(
            wda_url=self.wda_url,
            session_id=self.session_id,
            device_id=self.device_id,
        )
        app_name = get_current_app(
            wda_url=self.wda_url,
            session_id=self.session_id,
        )

        ui_nodes: list[Any] = []
        ui_texts: list[str] = []

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
                ui_nodes = []
                ui_texts = []

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
            ui_tree=None,
            ui_nodes=ui_nodes,
            ui_texts=ui_texts,
            screen_hash=screen_hash,
            timestamp=time.time(),
        )

"""Skills 自迭代的样本采集与生成辅助。"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from phone_agent.skills.observation import Observation
from phone_agent.skills.utils import decode_image_from_base64


@dataclass
class CasePack:
    """记录未知场景的样本包。"""

    case_id: str
    task: str
    reason: str
    timestamp: float
    app_name: str | None
    device_id: str | None
    skill_id: str | None
    step_id: str | None
    error_code: str | None
    error_message: str | None
    screen_hash: str | None
    ocr_texts: list[str]
    ocr_nodes: list[dict[str, Any]]
    action_history: list[dict[str, Any]]
    extra: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """将样本包序列化为可写入 JSON 的字典。"""
        # 关键步骤：序列化样本包
        return {
            "case_id": self.case_id,
            "task": self.task,
            "reason": self.reason,
            "timestamp": self.timestamp,
            "app_name": self.app_name,
            "device_id": self.device_id,
            "skill_id": self.skill_id,
            "step_id": self.step_id,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "screen_hash": self.screen_hash,
            "ocr_texts": self.ocr_texts,
            "ocr_nodes": self.ocr_nodes,
            "action_history": self.action_history,
            "extra": self.extra,
        }


class SkillLearningRecorder:
    """负责采集失败场景并落盘为 Case Pack。"""

    def __init__(self, cases_dir: str = "skills/_cases") -> None:
        """初始化样本采集器并配置落盘目录。"""
        # 关键步骤：准备样本存储目录
        self.cases_dir = Path(cases_dir)
        self.cases_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_env(cls) -> "SkillLearningRecorder | None":
        """从环境变量创建采集器，未开启时返回 None。"""
        # 关键步骤：根据环境变量决定是否启用
        if os.getenv("PHONE_AGENT_SKILL_LEARNING", "0") not in ("1", "true", "yes"):
            return None
        cases_dir = os.getenv("PHONE_AGENT_SKILL_CASES_DIR", "skills/_cases")
        return cls(cases_dir=cases_dir)

    def record_case(
        self,
        task: str,
        reason: str,
        observation: Observation | None,
        skill_id: str | None = None,
        step_id: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        action_history: list[dict[str, Any]] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> Path:
        """保存未知场景样本，并返回样本目录路径。"""
        # 关键步骤：生成样本包并落盘
        timestamp = time.time()
        case_id = f"case_{int(timestamp)}_{int(timestamp * 1000) % 1000:03d}"
        case_dir = self.cases_dir / time.strftime("%Y%m%d", time.localtime(timestamp)) / case_id
        case_dir.mkdir(parents=True, exist_ok=True)

        app_name = None
        device_id = None
        screen_hash = None
        ocr_texts: list[str] = []
        ocr_nodes: list[dict[str, Any]] = []

        if observation is not None:
            app_name = getattr(observation, "app_name", None)
            device_id = getattr(observation, "device_id", None)
            screen_hash = getattr(observation, "screen_hash", None)
            ocr_texts = list(getattr(observation, "ui_texts", []) or [])
            for node in getattr(observation, "ui_nodes", []) or []:
                ocr_nodes.append(
                    {
                        "text": getattr(node, "text", ""),
                        "bounds": getattr(node, "bounds", None),
                        "class_name": getattr(node, "class_name", None),
                    }
                )

        pack = CasePack(
            case_id=case_id,
            task=task,
            reason=reason,
            timestamp=timestamp,
            app_name=app_name,
            device_id=device_id,
            skill_id=skill_id,
            step_id=step_id,
            error_code=error_code,
            error_message=error_message,
            screen_hash=screen_hash,
            ocr_texts=ocr_texts,
            ocr_nodes=ocr_nodes,
            action_history=action_history or [],
            extra=extra or {},
        )

        (case_dir / "case.json").write_text(
            json.dumps(pack.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        if observation is not None and getattr(observation, "screenshot", None):
            screenshot_data = getattr(observation.screenshot, "base64_data", None)
            if screenshot_data:
                image = decode_image_from_base64(screenshot_data)
                image.save(case_dir / "screenshot.png")

        return case_dir

    def record_shadow_match(
        self,
        task: str,
        observation: Observation | None,
        skill_id: str,
        reason: str = "shadow-match",
    ) -> Path:
        """记录 shadow 命中事件，便于人工审核。"""
        # 关键步骤：保存 shadow 命中样本
        return self.record_case(
            task=task,
            reason=reason,
            observation=observation,
            skill_id=skill_id,
        )

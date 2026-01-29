#!/usr/bin/env python3
"""从 Case Pack 自动生成 shadow Skills。"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any

import yaml


def _slugify(value: str) -> str:
    text = re.sub(r"\s+", "_", value.strip())
    text = re.sub(r"[^0-9a-zA-Z_\-\u4e00-\u9fff]", "", text)
    return text[:40] if text else "unknown"


def _pick_primary_text(texts: list[str]) -> str | None:
    for text in texts:
        stripped = text.strip()
        if 0 < len(stripped) <= 8:
            return stripped
    return texts[0].strip() if texts else None


def _build_keywords(task: str, ocr_texts: list[str]) -> list[str]:
    keywords: list[str] = []
    if task:
        keywords.append(task[:20])
    for text in ocr_texts:
        stripped = text.strip()
        if not stripped:
            continue
        if len(stripped) > 8:
            continue
        if stripped in keywords:
            continue
        keywords.append(stripped)
        if len(keywords) >= 8:
            break
    return keywords


def build_skill_spec(case: dict[str, Any]) -> dict[str, Any]:
    task = case.get("task", "")
    app_name = case.get("app_name")
    ocr_texts = case.get("ocr_texts", []) or []
    case_id = case.get("case_id", "unknown")
    reason = case.get("reason", "unknown")

    primary_text = _pick_primary_text(ocr_texts)
    steps: list[dict[str, Any]] = []
    if primary_text:
        steps.append(
            {
                "id": "tap_primary",
                "action": "tap",
                "target": {
                    "selector": {"text": primary_text, "match": "contains"}
                },
            }
        )
    else:
        steps.append({"id": "wait_default", "action": "wait", "duration": "1s"})

    return {
        "id": "auto_" + _slugify(app_name or "app") + f"_{int(time.time())}",
        "name": f"自动生成（shadow）-{app_name or 'unknown'}",
        "version": "0.1",
        "level": 2,
        "role": "flow",
        "owner": "system2",
        "status": "shadow",
        "routing": {
            "keywords": _build_keywords(task, ocr_texts),
            "priority": 1,
            **({"require_app": app_name} if app_name else {}),
        },
        "meta": {
            "source_case": case_id,
            "reason": reason,
        },
        "steps": steps,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Auto-generate shadow skills from Case Packs")
    parser.add_argument("case_dir", type=str, help="Case pack directory (contains case.json)")
    parser.add_argument(
        "--output-dir",
        type=str,
        default="skills/shadow",
        help="Output dir for generated skills",
    )
    args = parser.parse_args()

    case_dir = Path(args.case_dir)
    case_path = case_dir / "case.json"
    if not case_path.exists():
        raise SystemExit(f"case.json not found in {case_dir}")

    case = json.loads(case_path.read_text(encoding="utf-8"))
    spec = build_skill_spec(case)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{spec['id']}.yaml"
    output_path.write_text(
        yaml.safe_dump(spec, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    print(f"Generated shadow skill: {output_path}")


if __name__ == "__main__":
    main()

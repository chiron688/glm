#!/usr/bin/env python3
"""Run a skill directly with optional recording/playback."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from phone_agent.skills import (
    SkillRegistry,
    SkillRunner,
    SkillRunnerConfig,
    TesseractOcrProvider,
)


def _parse_inputs(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a skill")
    parser.add_argument("--skills-dir", nargs="*", default=["skills"], help="Skills directory list")
    parser.add_argument("--skill-id", required=True, help="Skill ID")
    parser.add_argument("--inputs", default=None, help="JSON inputs")
    parser.add_argument("--common-handlers", default=None, help="Common handlers YAML")
    parser.add_argument("--record-dir", default=None, help="Record observations to directory")
    parser.add_argument("--playback-dir", default=None, help="Replay observations from directory")
    parser.add_argument("--use-ocr", action="store_true", help="Enable Tesseract OCR")
    parser.add_argument("--dry-run", action="store_true", help="Do not execute device actions")

    args = parser.parse_args()

    registry = SkillRegistry()
    registry.load_from_paths([Path(path) for path in args.skills_dir])

    ocr_provider = TesseractOcrProvider() if args.use_ocr else None
    dry_run = args.dry_run or bool(args.playback_dir)

    runner = SkillRunner(
        registry,
        SkillRunnerConfig(
            common_error_handlers_path=args.common_handlers,
            record_dir=args.record_dir,
            playback_dir=args.playback_dir,
            ocr_provider=ocr_provider,
            dry_run=dry_run,
        ),
    )

    result = runner.run(args.skill_id, _parse_inputs(args.inputs))
    print(f"success={result.success}")
    print(f"message={result.message}")
    if result.error:
        print(f"error={result.error.code.value} stage={result.error.stage}")


if __name__ == "__main__":
    main()

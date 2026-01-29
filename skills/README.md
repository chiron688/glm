# Skills

This folder contains YAML skills and the schema that defines them.

## Structure

- `schema/skill.schema.yaml`: JSON Schema for skill definitions.
- `common/vocab.yaml`: Shared regex vocabulary for selectors.
- `examples/`: Example skills demonstrating retries, guards, and handlers.
- `level1/`: Atomic skills intended for System1 execution.
- `level2/`: Flow skills intended for System2 planning and System1 execution.
- `level3/`: Recovery skills intended for System2 escalation.

## COTA layering metadata

Skills can declare optional metadata fields to participate in the COTA layered routing:

- `level`: `1` (atomic), `2` (flow), `3` (recovery)
- `role`: `atomic`, `flow`, `recovery`
- `owner`: `system1` or `system2`
- `latency_target_ms`, `sampling_hz`: optional performance hints

Recovery-only skills should include a `routing` block that does not match normal tasks (e.g. a sentinel keyword)
so they are invoked explicitly by System2 rather than the generic task router.

## Runtime usage

```python
from phone_agent.skills import SkillRegistry, SkillRunner, SkillRunnerConfig

registry = SkillRegistry()
registry.load_from_paths(["skills/examples"])

runner = SkillRunner(registry, SkillRunnerConfig())
result = runner.run("video_publish_template", {"video_path": "/path/to.mp4", "caption": "Hello"})
print(result.success, result.message)
```

## Router usage

```python
from phone_agent.skills import SkillRegistry, SkillRouter, SkillRouterConfig

registry = SkillRegistry()
registry.load_from_paths(["skills/examples"])
router = SkillRouter(
    registry,
    SkillRouterConfig(
        enforce_skill_whitelist=True,
        skill_whitelist=["publish_video_suite"],
        enforce_on_risk=True,
        risk_keywords=["发布", "上传", "post", "upload", "publish"],
    ),
)
decision = router.select("上传视频到 TikTok", observation=None)
```

## CLI runner

```bash
python scripts/run_skill.py --skill-id publish_video_suite --inputs '{"caption":"Hello"}'
```

## Notes

- UI tree capture is disabled to reduce detection risk. `selector` resolution is OCR-based only.
- OCR requires an OCR provider; without OCR, only coordinate targets will work.
- Android COTA 默认强制使用 PaddleOCR v5 多语言模型（`lang=ml`，`force_v5=True`）。
- 可通过环境变量切换 OCR 供应商：
  - `PHONE_AGENT_OCR_PROVIDER=paddle|gemma`
  - PaddleOCR：`PHONE_AGENT_OCR_LANG=ml`
  - Gemma OCR：`PHONE_AGENT_OCR_BASE_URL`、`PHONE_AGENT_OCR_API_KEY`、`PHONE_AGENT_OCR_MODEL`
    （默认模型：`google/gemma-3n-E2B-it-litert-lm`）
- Gemma OCR 需要模型端返回 JSON（含文本与像素级边界框）。
- `preconditions`, `guard`, and `assert` accept condition blocks with optional timeouts.
- `error_handlers` can auto-dismiss popups before each step or handle errors during a step.
- Use `skills/common/error_handlers.yaml` for common popups (permissions, update prompts, network, login).
- Recording/playback: set `SkillRunnerConfig.record_dir` to record, or `playback_dir` to replay.
- OCR selectors: pass an OCR provider (e.g. `TesseractOcrProvider`) in `SkillRunnerConfig.ocr_provider`.
- `RunSkill` can be used in steps or handlers to compose workflows.
- `vocab_path` can be set in a skill to load shared regex selectors (see `skills/common/vocab.yaml`). By default the runner loads `skills/common/vocab.yaml` for all skills.

## Error codes

Common `codes` values for handlers:

- `PRECONDITION_FAILED`
- `PRECONDITION_UNKNOWN`
- `SCREEN_MISMATCH`
- `TARGET_NOT_FOUND`
- `ACTION_FAILED`
- `ACTION_EXCEPTION`
- `POSTCONDITION_FAILED`
- `TIMEOUT`
- `DEVICE_ERROR`
- `ERROR_SCREEN_DETECTED`
- `HANDLER_FAILED`
- `ABORTED`
- `UNKNOWN`

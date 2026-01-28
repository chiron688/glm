# Skills

This folder contains YAML skills and the schema that defines them.

## Structure

- `schema/skill.schema.yaml`: JSON Schema for skill definitions.
- `examples/`: Example skills demonstrating retries, guards, and handlers.

## Runtime usage

```python
from phone_agent.skills import SkillRegistry, SkillRunner, SkillRunnerConfig

registry = SkillRegistry()
registry.load_from_paths(["skills/examples"])

runner = SkillRunner(registry, SkillRunnerConfig())
result = runner.run("video_publish_template", {"video_path": "/path/to.mp4", "caption": "Hello"})
print(result.success, result.message)
```

## Notes

- `selector` targets require a UI hierarchy dump. On ADB this uses `uiautomator dump`.
- `preconditions`, `guard`, and `assert` accept condition blocks with optional timeouts.
- `error_handlers` can auto-dismiss popups before each step or handle errors during a step.
- Use `skills/common/error_handlers.yaml` for common popups (permissions, update prompts, network, login).
- Recording/playback: set `SkillRunnerConfig.record_dir` to record, or `playback_dir` to replay.
- OCR selectors: pass an OCR provider (e.g. `TesseractOcrProvider`) in `SkillRunnerConfig.ocr_provider`.

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

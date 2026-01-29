# COTA + Skills Architecture

This document describes the dual-system COTA execution model and how it maps to the current codebase.

## Layers

User Task
  -> Orchestrator (Layer 4)
  -> COTA Core (System2 planning + System1 execution)
  -> Skills Library (Layer 2, with levels)
  -> Device Control (Layer 1)

## Core Components

- `phone_agent/cota/coordinator.py`
  Orchestrates System2 planning and System1 execution. Handles skill failures and recovery.

- `phone_agent/cota/system2.py`
  Slow planning system. Routes tasks to flow skills (Level 2) or falls back to the LLM agent.
  Also maps skill errors to recovery skills (Level 3) and can invoke a VLM analyzer for semantic recovery.

- `phone_agent/cota/system1.py`
  Fast reaction system. Executes atomic intents with light jitter and timing control.

- `phone_agent/cota/agent.py`
  `COTAPhoneAgent` wrapper that wires the coordinator, skills, and fallback LLM agent.

## Skills Layering

Skills can declare optional metadata to indicate their layer and ownership:

- `level: 1` / `role: atomic` / `owner: system1`
- `level: 2` / `role: flow` / `owner: system2`
- `level: 3` / `role: recovery` / `owner: system2`

See `skills/README.md` and `skills/schema/skill.schema.yaml` for details.

## Execution Flow (Simplified)

1. System2 builds a plan using skill routing or LLM fallback.
2. System1 executes intents or Skills Runner executes flow skills.
3. On failure, System2 maps errors to recovery skills or falls back to LLM.

## Extension Points

- Add Level 1 atomic skills for gesture primitives.
- Add Level 2 flow skills for app workflows.
- Add Level 3 recovery skills for popups, UI changes, network errors.
- Enable VLM-based exception analyzer by setting `COTAConfig.system2.enable_vlm_recovery = True`
  and optionally providing `COTAConfig.vlm_analyzer` overrides.

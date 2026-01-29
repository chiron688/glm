# 整体流程说明（仅 COTA）

本文档用于说明项目的端到端执行流程，当前仅保留 **COTA 双系统** 路径，以及 Skills 的路由、执行与恢复机制。

---

## 1）总体架构

```
用户任务
  └─ COTA 引擎（System2 + System1）
        ├─ Skills 路由（选择流程技能）
        ├─ Skill Runner（执行步骤 + 处理器）
        └─ VLM 异常恢复（可选）
```

核心模块：

- Skills 框架：`phone_agent/skills/*`
- COTA 引擎：`phone_agent/cota/*`
- CLI 入口：`main.py`

---

## 2）COTA 双系统流程

**入口**：`COTAPhoneAgent.run(task)`（`phone_agent/cota/agent.py`）

> iOS 入口：`COTAIOSAgent.run(task)`（`phone_agent/cota/agent_ios.py`），iOS 依赖截图 + OCR（默认启用），不支持 UI 树选择器。

### 2.1 System2（慢思考）规划
- 模块：`phone_agent/cota/system2.py`
- System2 先进行任务规划：
  - 若路由到技能 → `PlanStep(kind=SKILL)`
  - 若无法路由 → 直接返回“无匹配技能”

### 2.2 System1（快反应）执行
- 模块：`phone_agent/cota/system1.py`
- 负责原子动作执行（Tap/Swipe/Type/Wait/Back/Home）
- 带轻量抖动、动作节奏、活性维护（可选）

### 2.3 Skills 执行器
- 模块：`phone_agent/skills/runner.py`
- 执行 YAML 技能步骤
- 每个步骤支持：
  - `guard` / `assert`（前后检查）
  - `retry`（失败重试）
  - `error_handlers`（异常处理器）
- 支持 `RunSkill` 进行技能组合
- UI 树采集已关闭，`selector` 仅通过 OCR 文本节点匹配或坐标点击（未启用 OCR 时只能使用坐标）。Android COTA 默认强制使用 PaddleOCR v5 多语言模型（`lang=ml`，`force_v5=True`）。
- 可通过环境变量切换 OCR 供应商：
  - `PHONE_AGENT_OCR_PROVIDER=paddle|gemma`
  - PaddleOCR：`PHONE_AGENT_OCR_LANG=ml`
  - Gemma OCR：`PHONE_AGENT_OCR_BASE_URL`、`PHONE_AGENT_OCR_API_KEY`、`PHONE_AGENT_OCR_MODEL`
  - Gemma OCR 需要模型端返回 JSON（文本 + 像素级边界框）

### 2.4 异常恢复流程
技能失败后：
1. 若需要人工接管 → 立即结束并提示。
2. 若启用 VLM 恢复 → 调用 VLM 对截图+错误语义分析，选择恢复技能。
3. 否则使用静态映射（错误码 → 恢复技能）。
4. 恢复成功后会重试原步骤/技能。
5. 恢复失败则结束并返回错误信息。

---

## 3）Skills 路由与分层

### 3.1 路由机制
- 路由器：`phone_agent/skills/router.py`
- 评分依据：
  - `routing.keywords`
  - `routing.task_regex`
  - `routing.require_app`
  - `routing.priority`
- 风险控制（risk gate）：对于高风险任务，可强制只走 Skills。

### 3.2 分层字段（COTA）
Skills 可声明如下元数据：

- `level: 1` / `role: atomic` / `owner: system1`
- `level: 2` / `role: flow` / `owner: system2`
- `level: 3` / `role: recovery` / `owner: system2`

### 3.3 恢复技能的路由哨兵
恢复技能一般不参与正常任务路由，因此会在 `routing` 中加入哨兵关键词（如 `__recovery__`）以避免误选。

---

## 4）Skills 错误处理机制

SkillRunner 的错误处理逻辑：
- 技能级 `preconditions` / `postconditions`
- 步骤级 `guard` / `assert`
- `error_handlers` 可执行：
  - RunSkill
  - Tap / Swipe / Wait
  - retry / backoff
  - escalate（人工接管）

常见错误码：
- `PRECONDITION_FAILED`
- `TARGET_NOT_FOUND`
- `ACTION_FAILED`
- `POSTCONDITION_FAILED`

COTA 默认映射：
- `SCREEN_MISMATCH` → `adapt_ui_change`
- `ACTION_FAILED` → `handle_interaction_error`
- `DEVICE_ERROR` → `handle_device_error`
- `POSTCONDITION_FAILED` → `handle_postcondition_error`

---

## 5）VLM 异常恢复（可选）

模块：`phone_agent/cota/vlm_analyzer.py`

启用后：
1. System2 捕获最新截图 + 错误信息。
2. 发送给 VLM，返回 JSON 结构化诊断。
3. 根据 `suggested_skill` 选择恢复技能。
4. 若 `confidence` 高于阈值，则执行恢复。

启用方式：
```python
cota_config = COTAConfig()
# 默认已启用；如需关闭可显式设为 False
cota_config.system2.enable_vlm_recovery = True
```

启用 VLM 恢复时需要可用的模型 API（本地 vLLM 也需要 base_url；api_key 可为空或占位）。运行时会进行连通性检查。

---

## 6）示例：TikTok 上传流程（COTA）

任务：`"上传视频到 TikTok"`

1. 路由器选择 `tiktok_upload_v2`（Level 2）。
2. SkillRunner 依次执行：
   - `publish_open_create`
   - `publish_select_upload`
   - `publish_pick_asset`
   - `publish_edit_caption`
   - `publish_post`
   - `publish_verify_post_strict`
3. 若出现登录/权限/更新弹窗，使用 `skills/common/error_handlers.yaml` 处理。
4. 若 UI 变化，触发恢复技能（如 `adapt_ui_change`）。

---

## 7）示例：养号浏览片段

技能：`tiktok_nurture_browse_segment`

执行逻辑：
- 启动 TikTok
- 等待
- 多次滑动 + 等待

该技能仅是“片段”，长时间养号应由外部调度器循环调用并结合记忆管理。

---

## 8）CLI 使用

COTA 引擎（Android/HarmonyOS）：
```bash
python main.py "上传视频到 TikTok"
```

COTA 引擎（iOS）：
```bash
python main.py --device-type ios "打开Safari搜索iPhone技巧"
```

---

## 9）扩展方向

- 在 `skills/level2/` 新增流程技能
- 在 `skills/level3/` 新增恢复技能
- 在 `phone_agent/cota/system1.py` 扩展运动原语
- 在 `phone_agent/cota/vlm_analyzer.py` 定制 VLM 提示词

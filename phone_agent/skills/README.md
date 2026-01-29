# skills 模块说明

## 作用
提供 Skills 的加载、路由、执行与恢复机制，并通过 OCR 构建可选择的 UI 文本节点。

## 核心文件
- `registry.py` / `loader.py`：技能注册与加载。
- `router.py`：技能路由与风险控制。
- `runner.py`：技能步骤执行、校验与错误处理。
- `conditions.py` / `common_handlers.py`：条件判断与通用恢复。
- `selector.py`：基于 OCR 节点与坐标的元素选择。
- `ocr.py`：OCR 供应商封装（PaddleOCR / Gemma）。
- `observation.py` / `observation_ios.py`：观察采集（截图 + OCR）。
- `schema.py` / `errors.py` / `reporting.py`：结构、错误与报告。

## 主要能力
- 技能 YAML 解析、步骤编排、重试与断言。
- OCR 驱动的文本选择器与坐标点击。
- 错误处理与恢复技能调度。

## OCR 说明
- 默认使用 PaddleOCR v5 多语言模型（`lang=ml`，`force_v5=True`）。
- 可通过环境变量切换 OCR 供应商：
  - `PHONE_AGENT_OCR_PROVIDER=paddle|gemma`
  - `PHONE_AGENT_OCR_LANG=ml`
  - `PHONE_AGENT_OCR_BASE_URL` / `PHONE_AGENT_OCR_API_KEY` / `PHONE_AGENT_OCR_MODEL`
- UI 树采集已禁用，仅保留 OCR + 坐标路径。

## 与其它模块关系
- 由 `cota/system2.py` 进行路由与规划。
- 由 `actions` 与设备控制层执行技能动作。

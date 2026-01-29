# cota 模块说明

## 作用
实现 COTA 双系统引擎：System2（慢思考规划）+ System1（快反应执行），并提供异常恢复与协同机制。

## 核心文件
- `agent.py` / `agent_ios.py`：COTA 入口代理（Android/HarmonyOS 与 iOS）。
- `system2.py`：慢思考规划器，负责任务分解与技能路由。
- `system1.py`：快反应执行器，负责原子动作与活性维护。
- `coordinator.py`：双系统协同调度与步骤推进。
- `vlm_analyzer.py`：异常恢复时的视觉语义分析。
- `config.py` / `types.py`：配置与类型定义。

## 主要能力
- 根据任务选择 Skills 或直接规划步骤。
- System1 高频执行动作，System2 异常唤醒与恢复。
- 支持 VLM 异常恢复（截图 + 错误语义）。

## 配置要点
- `COTAConfig` 控制系统 1/2 行为、恢复策略与阈值。
- 可通过环境变量选择 OCR 供应商（PaddleOCR / Gemma）。

## 与其它模块关系
- 依赖 `skills` 执行技能与恢复流程。
- 依赖 `actions` 与 `device_factory` 执行动作。
- 依赖 `model` 调用 LLM/VLM 服务。

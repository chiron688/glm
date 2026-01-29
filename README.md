# Open-AutoGLM

Open-AutoGLM（Phone Agent）是一个 **AI 驱动的手机自动化框架**，通过 OpenAI 兼容的模型 API 理解屏幕内容并执行操作，支持 Android / HarmonyOS / iOS 设备。

## 功能亮点

- **自然语言任务**：一句话驱动手机完成应用内操作
- **多平台设备支持**：Android（ADB）、HarmonyOS（HDC）、iOS（WebDriverAgent）
- **两种执行引擎**：LLM 直接执行或 COTA（计划 + 恢复）
- **Skills 体系**：可扩展的技能库与路由机制
- **可观测性**：verbose 输出、分步执行、性能指标
- **远程设备**：支持 TCP/IP 连接与多设备场景

## 运行前准备

- Python >= 3.10
- 一个 **OpenAI 兼容的模型服务**（支持 chat.completions）
- 设备工具链：
  - Android：`adb`（推荐安装 Android Platform Tools）
  - HarmonyOS：`hdc`
  - iOS：`libimobiledevice` + WebDriverAgent（macOS + Xcode）

## 安装

```bash
pip install -r requirements.txt
pip install -e .
```

## 快速开始

### 1) CLI（Android 默认）

```bash
# 交互模式
python main.py

# 直接执行任务
python main.py "打开小红书搜索美食攻略"

# 指定模型服务
python main.py --base-url http://localhost:8000/v1 --model autoglm-phone-9b

# 使用 COTA 引擎（Android/HarmonyOS）
python main.py --engine cota "上传视频到 TikTok"
```

### 2) HarmonyOS（HDC）

```bash
python main.py --device-type hdc "打开设置查看版本信息"
```

### 3) iOS（WDA）

```bash
# iOS 设备（通过 main.py）
python main.py --device-type ios --wda-url http://localhost:8100 "Open Safari and search for iPhone tips"

# 或使用 ios.py
python ios.py --base-url http://localhost:8000/v1 --model autoglm-phone-9b --wda-url http://localhost:8100 "TASK"
```

iOS 环境配置请参考：`docs/ios_setup/ios_setup.md`

### 4) Python API

```python
from phone_agent import PhoneAgent
from phone_agent.agent import AgentConfig
from phone_agent.model import ModelConfig

model_config = ModelConfig(
    base_url="http://localhost:8000/v1",
    model_name="autoglm-phone-9b",
)
agent_config = AgentConfig(max_steps=50, verbose=True, lang="cn")

agent = PhoneAgent(model_config=model_config, agent_config=agent_config)
result = agent.run("打开淘宝搜索无线耳机并加入购物车")
print(result)
```

更多示例见：`examples/basic_usage.py`

### 5) 集群模式（多设备）

```bash
# Android/HarmonyOS：使用全部已连接设备并行执行
python main.py --all-devices "打开抖音浏览10分钟"

# iOS：多设备需提供对应的 WDA 地址
python main.py --device-type ios \
  --device-ids <udid1>,<udid2> \
  --wda-urls http://localhost:8100,http://localhost:8101 \
  "打开Safari搜索iPhone技巧"

# 顺序执行
python main.py --all-devices --sequential "打开抖音浏览10分钟"
```

## 常用命令

```bash
# 列出连接设备
python main.py --list-devices

# 连接远程设备
python main.py --connect 192.168.1.100:5555

# 断开远程设备
python main.py --disconnect 192.168.1.100:5555

# 开启 TCP/IP 调试（USB 设备）
python main.py --enable-tcpip

# 列出支持的应用
python main.py --list-apps
```

## 模型服务部署检查

项目提供简单的推理检查脚本：

```bash
python scripts/check_deployment_cn.py \
  --base-url http://localhost:8000/v1 \
  --apikey EMPTY \
  --model autoglm-phone-9b
```

英文版本：`scripts/check_deployment_en.py`

## 模型部署方式（示例）

Phone Agent 通过 **OpenAI 兼容 API** 调用模型，并会上传屏幕截图（`image_url` base64）进行视觉理解。只要你的服务支持 `chat.completions` 且可接收图片即可。

### 通用步骤

1. 启动一个 OpenAI 兼容的模型服务（支持多模态输入）
2. 记录 `base_url` 与 `model` 名称
3. 设置环境变量或 CLI 参数
4. 用部署检查脚本验证输出

```bash
export PHONE_AGENT_BASE_URL=http://localhost:8000/v1
export PHONE_AGENT_MODEL=autoglm-phone-9b
export PHONE_AGENT_API_KEY=EMPTY

python scripts/check_deployment_cn.py --base-url $PHONE_AGENT_BASE_URL --model $PHONE_AGENT_MODEL
```

### 参考示例（仅作示意，参数以各自版本为准）

```bash
# vLLM 示例
vllm serve /path/to/your-vlm-model \
  --served-model-name autoglm-phone-9b \
  --host 0.0.0.0 --port 8000

# sglang 示例
python -m sglang.launch_server \
  --model-path /path/to/your-vlm-model \
  --host 0.0.0.0 --port 8000
```

> 注意：不同框架/版本的启动参数可能不一致，请以对应文档为准。

## 基准测试（待补充）

目前仓库未内置统一的 Benchmark 脚本，可按以下流程记录关键指标并整理到表格中：

1. 选定任务集合（建议覆盖：搜索、表单输入、列表筛选、跨 App 操作等）
2. 固定设备与模型版本，记录运行配置（`base_url`、`model`、`max_steps`）
3. 运行任务并记录输出（成功率、平均步数、总耗时、失败原因）
4. 填写结果表并在 README 更新

**结果表模板（示例）**：

| 日期 | 设备 | 模型 | 引擎 | 任务数 | 成功率 | 平均步数 | 平均耗时 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-01-01 | Pixel 7 / Android 14 | autoglm-phone-9b | llm | 20 | TBD | TBD | TBD | 待补充 |

## Skills 与 COTA

- Skills 目录与规范：`skills/README.md`
- COTA 架构说明：`docs/cota_architecture.md`
- 运行单个技能：

```bash
python scripts/run_skill.py --skill-id publish_video_suite --inputs '{"caption":"Hello"}'
```

## 环境变量

可通过环境变量覆盖默认配置：

- `PHONE_AGENT_BASE_URL`：模型 API base URL（默认 `http://localhost:8000/v1`）
- `PHONE_AGENT_MODEL`：模型名称（默认 `autoglm-phone-9b`）
- `PHONE_AGENT_API_KEY`：API Key（默认 `EMPTY`）
- `PHONE_AGENT_MAX_STEPS`：最大步数（默认 `100`）
- `PHONE_AGENT_DEVICE_ID`：设备 ID
- `PHONE_AGENT_DEVICE_IDS`：多设备 ID（逗号分隔）
- `PHONE_AGENT_DEVICE_TYPE`：`adb` / `hdc` / `ios`
- `PHONE_AGENT_ENGINE`：`llm` / `cota`
- `PHONE_AGENT_LANG`：`cn` / `en`
- `PHONE_AGENT_WDA_URL`：iOS WDA URL（默认 `http://localhost:8100`）
- `PHONE_AGENT_WDA_URLS`：iOS 多设备 WDA URL（逗号分隔）

## 目录结构

```
.
├─ phone_agent/         # 核心库
├─ scripts/             # 部署检查、技能运行等工具
├─ examples/            # 使用示例
├─ skills/              # Skills 体系
├─ docs/                # 文档与架构说明
├─ main.py              # CLI（Android/HarmonyOS/iOS）
└─ ios.py               # iOS CLI
```

## 常见问题

- **COTA 不支持 iOS**：当前仅对 Android / HarmonyOS 启用 COTA，iOS 将回退到 LLM 引擎。
- **ADB Keyboard 缺失**：Android 设备需安装 ADB Keyboard，CLI 会在启动时检查并提示。

---

如需补充更多内容（部署指南、App 适配清单、Benchmark 等），可以告诉我希望的结构与重点。

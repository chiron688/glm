# phone_agent 包说明

## 作用
`phone_agent` 是项目的核心库，负责将“观察 → 规划 → 动作执行”的流程落地到真实设备，支持 Android（ADB）、HarmonyOS（HDC）与 iOS（WDA/XCTest）。

## 模块概览
- `actions/`：模型动作解析与执行（Tap/Swipe/Type/Wait 等）。
- `adb/` / `hdc/` / `xctest/`：不同平台的设备连接、截图、输入与控制。
- `cota/`：COTA 双系统引擎（System2 规划 + System1 执行）。
- `skills/`：Skills 注册、路由、执行与恢复机制（OCR 驱动）。
- `model/`：OpenAI 兼容模型调用客户端与配置。
- `config/`：提示词、应用映射、时间配置与本地化。

## 主要入口
- `PhoneAgent`：传统 LLM 驱动的单代理执行（Android/iOS/HarmonyOS）。
- `COTAPhoneAgent` / `COTAIOSAgent`：COTA 引擎入口。
- `ClusterRunner`：多设备集群调度入口（并行/顺序）。

## 关键依赖与约束
- 需要 OpenAI 兼容的模型 API（可本地部署）。
- 设备工具：Android 需要 ADB，HarmonyOS 需要 HDC，iOS 需要 WDA 与 libimobiledevice。
- Skills 默认使用 OCR（UI 树采集已禁用）。

## 典型用法
```python
from phone_agent.cota import COTAPhoneAgent
from phone_agent.model import ModelConfig
from phone_agent.agent import AgentConfig

agent = COTAPhoneAgent(
    model_config=ModelConfig(base_url="http://localhost:8000/v1"),
    agent_config=AgentConfig(max_steps=80)
)
print(agent.run("打开抖音浏览10分钟"))
```

# config 模块说明

## 作用
集中维护提示词、应用映射、时间参数与多语言配置，作为系统级配置来源。

## 核心文件
- `prompts.py` / `prompts_zh.py` / `prompts_en.py`：系统提示词与模板。
- `apps.py` / `apps_harmonyos.py` / `apps_ios.py`：应用名到包名/BundleID 的映射。
- `timing.py`：动作节奏、等待与延迟配置。
- `i18n.py`：语言与本地化支持。
- `__init__.py`：对外暴露的配置入口。

## 主要能力
- 为模型提供统一的系统提示词与任务模板。
- 统一应用命名与平台差异映射。
- 控制动作节奏，提升自然性与稳定性。

## 使用场景
- `PhoneAgent` / `COTAPhoneAgent` 初始化系统提示词。
- `ActionHandler` 的动作时序控制。

## 维护建议
新增应用时优先在对应平台映射表中补充，保持命名一致（如 "TikTok"、"抖音"）。

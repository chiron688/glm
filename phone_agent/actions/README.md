# actions 模块说明

## 作用
处理模型输出的动作指令，并将其转为真实设备上的点击、滑动、输入、等待等操作。

## 核心文件
- `handler.py`：Android/HarmonyOS 动作处理器，解析动作并通过 ADB/HDC 执行。
- `handler_ios.py`：iOS 动作处理器，通过 WebDriverAgent 执行操作。
- `__init__.py`：动作处理器导出入口。

## 主要能力
- 动作类型解析与校验（Tap/Swipe/Type/Wait/Back/Home 等）。
- 设备分辨率坐标转换与归一化坐标适配。
- 敏感操作确认与人工接管回调。
- 操作失败兜底与错误信息返回。

## 与其它模块关系
- 依赖 `device_factory` 调用 ADB/HDC。
- iOS 动作依赖 `xctest` 模块与 WDA 服务。
- 与 `skills/runner.py` 协作执行技能步骤中的动作。

## 扩展建议
如需新增动作类型，可在 `handler.py` 与 `handler_ios.py` 中注册对应处理函数，并补充参数校验与错误处理。

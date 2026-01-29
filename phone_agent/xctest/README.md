# xctest 模块说明

## 作用
通过 WebDriverAgent（WDA）/XCUITest 驱动 iOS 设备的截图、输入与应用控制。

## 核心文件
- `connection.py`：WDA 连接管理、设备列表、会话管理。
- `device.py`：点击、滑动、返回、Home、启动应用等动作封装。
- `input.py`：文本输入与清空。
- `screenshot.py`：获取截图并提供 base64 数据。
- `__init__.py`：统一导出。

## 主要能力
- WDA 状态检测与会话建立。
- iOS 设备输入操作封装（Tap/Swipe/LongPress 等）。
- 截图用于 OCR 与视觉模型分析。

## 注意事项
- 需要 macOS + Xcode + WebDriverAgent 运行环境。
- USB 模式建议使用 `iproxy` 做端口转发。

## 与其它模块关系
- 由 `COTAIOSAgent` 与 `IOSActionHandler` 直接调用。
- 与 `skills/observation_ios.py` 协同完成 OCR 观察。

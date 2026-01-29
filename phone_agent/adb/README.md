# adb 模块说明

## 作用
封装 Android 设备的 ADB 连接、截图、输入与控制接口，作为 Android 侧动作的底层实现。

## 核心文件
- `connection.py`：ADB 设备连接管理（USB/WiFi/远程）。
- `device.py`：应用启动、当前前台应用检测等设备信息能力。
- `input.py`：点击、滑动、长按、返回、Home 等动作封装。
- `screenshot.py`：截图获取与编码处理。
- `__init__.py`：统一导出。

## 主要能力
- 设备连接与断开（含 TCP/IP 方式）。
- 设备列表与基本信息查询。
- 通用输入动作封装（Tap/Swipe/LongPress/Type）。
- 截图获取并提供 base64 数据。

## 使用场景
- `PhoneAgent` 与 `COTAPhoneAgent` 的 Android 执行层。
- Skills 运行时的观察与动作执行。

## 注意事项
- 需要本机安装 ADB 工具，并确保设备已开启 USB 调试。
- 输入操作默认依赖 ADB Keyboard（可在系统检查中提示安装）。

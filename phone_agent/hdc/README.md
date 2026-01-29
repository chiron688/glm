# hdc 模块说明

## 作用
封装 HarmonyOS 设备的 HDC 连接、截图、输入与控制接口，作为 HarmonyOS 侧动作的底层实现。

## 核心文件
- `connection.py`：HDC 设备连接管理与列表查询。
- `device.py`：应用启动与当前应用识别。
- `input.py`：点击、滑动、长按、返回、Home 等动作封装。
- `screenshot.py`：截图获取与编码处理。
- `__init__.py`：统一导出。

## 主要能力
- HDC 设备管理（USB/远程）。
- 输入动作的统一封装与时序控制。
- 截图获取，为 OCR 与视觉模型提供输入。

## 环境与配置
- 本机需安装 HDC 工具并加入 PATH。
- 可通过环境变量 `HDC_VERBOSE=true` 开启命令详细日志。

## 与其它模块关系
- 被 `device_factory` 统一封装为设备实现。
- 与 `actions/handler.py`、`skills/runner.py` 配合完成执行。

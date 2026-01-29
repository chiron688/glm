# model 模块说明

## 作用
封装 OpenAI 兼容模型调用客户端与配置，统一多模态请求方式与响应解析。

## 核心文件
- `client.py`：模型请求客户端（chat.completions）。
- `__init__.py`：`ModelConfig` 与对外导出。

## 主要能力
- 管理模型服务地址、API Key、模型名与语言偏好。
- 支持图像输入（屏幕截图 base64）与文本提示组合。
- 为上层 `PhoneAgent` / `COTA` 提供统一接口。

## 配置示例
```python
from phone_agent.model import ModelConfig

cfg = ModelConfig(
    base_url="http://localhost:8000/v1",
    model_name="autoglm-phone-9b",
    api_key="EMPTY",
)
```

## 注意事项
- 需要模型服务支持 OpenAI 兼容的 `chat.completions` 接口。
- 图像输入以 `image_url` 形式传递（base64）。

"""使用 OpenAI 兼容 API 的 AI 推理模型客户端。"""

import json
import time
from dataclasses import dataclass, field
from typing import Any

from openai import OpenAI

from phone_agent.config.i18n import get_message


@dataclass
class ModelConfig:
    """AI 模型配置。"""

    base_url: str = "http://localhost:8000/v1"
    api_key: str = "EMPTY"
    model_name: str = "autoglm-phone-9b"
    max_tokens: int = 3000
    temperature: float = 0.0
    top_p: float = 0.85
    frequency_penalty: float = 0.2
    extra_body: dict[str, Any] = field(default_factory=dict)
    lang: str = "cn"  # 界面语言: 'cn' 或 'en'


@dataclass
class ModelResponse:
    """AI 模型响应。"""

    thinking: str
    action: str
    raw_content: str
    # 性能指标
    time_to_first_token: float | None = None  # 首 Token 延迟（秒）
    time_to_thinking_end: float | None = None  # 思考结束延迟（秒）
    total_time: float | None = None  # 总推理时间（秒）


class ModelClient:
    """
    与 OpenAI 兼容的视觉语言模型交互的客户端。

    参数:
        config: 模型配置。
    """

    def __init__(self, config: ModelConfig | None = None):
        self.config = config or ModelConfig()
        self.client = OpenAI(base_url=self.config.base_url, api_key=self.config.api_key)

    def request(self, messages: list[dict[str, Any]]) -> ModelResponse:
        """
        向模型发送请求。

        参数:
            messages: OpenAI 格式的消息字典列表。

        返回:
            包含思考与动作的 ModelResponse。

        异常:
            ValueError: 响应无法解析时抛出。
        """
        # 开始计时
        start_time = time.time()
        time_to_first_token = None
        time_to_thinking_end = None

        stream = self.client.chat.completions.create(
            messages=messages,
            model=self.config.model_name,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            top_p=self.config.top_p,
            frequency_penalty=self.config.frequency_penalty,
            extra_body=self.config.extra_body,
            stream=True,
        )

        raw_content = ""
        buffer = ""  # 用于暂存可能包含标记的内容
        action_markers = ["finish(message=", "do(action="]
        in_action_phase = False  # 是否进入动作阶段
        first_token_received = False

        for chunk in stream:
            if len(chunk.choices) == 0:
                continue
            if chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                raw_content += content

                # 记录首个 token 的时间
                if not first_token_received:
                    time_to_first_token = time.time() - start_time
                    first_token_received = True

                if in_action_phase:
                    # 已进入动作阶段，继续累积内容但不打印
                    continue

                buffer += content

                # 检查 buffer 中是否出现完整的标记
                marker_found = False
                for marker in action_markers:
                    if marker in buffer:
                        # 找到标记，打印其之前的内容
                        thinking_part = buffer.split(marker, 1)[0]
                        print(thinking_part, end="", flush=True)
                        print()  # 思考内容结束后换行
                        in_action_phase = True
                        marker_found = True

                        # 记录思考结束时间
                        if time_to_thinking_end is None:
                            time_to_thinking_end = time.time() - start_time

                        break

                if marker_found:
                    continue  # 继续收集剩余内容

                # 检查 buffer 是否以某个标记前缀结尾
                # 若是，则暂不打印（等待更多内容）
                is_potential_marker = False
                for marker in action_markers:
                    for i in range(1, len(marker)):
                        if buffer.endswith(marker[:i]):
                            is_potential_marker = True
                            break
                    if is_potential_marker:
                        break

                if not is_potential_marker:
                    # 可以安全打印 buffer
                    print(buffer, end="", flush=True)
                    buffer = ""

        # 计算总时间
        total_time = time.time() - start_time

        # 从响应中解析思考与动作
        thinking, action = self._parse_response(raw_content)

        # 打印性能指标
        lang = self.config.lang
        print()
        print("=" * 50)
        print(f"⏱️  {get_message('performance_metrics', lang)}:")
        print("-" * 50)
        if time_to_first_token is not None:
            print(
                f"{get_message('time_to_first_token', lang)}: {time_to_first_token:.3f}s"
            )
        if time_to_thinking_end is not None:
            print(
                f"{get_message('time_to_thinking_end', lang)}:        {time_to_thinking_end:.3f}s"
            )
        print(
            f"{get_message('total_inference_time', lang)}:          {total_time:.3f}s"
        )
        print("=" * 50)

        return ModelResponse(
            thinking=thinking,
            action=action,
            raw_content=raw_content,
            time_to_first_token=time_to_first_token,
            time_to_thinking_end=time_to_thinking_end,
            total_time=total_time,
        )

    def _parse_response(self, content: str) -> tuple[str, str]:
        """
        将模型响应解析为思考与动作两部分。

        解析规则:
        1. 若内容包含 'finish(message='，其前为思考，其后为动作。
        2. 若不满足规则 1 但包含 'do(action='，其前为思考，其后为动作。
        3. 兜底：若包含 '<answer>'，使用旧式 XML 标签解析。
        4. 否则返回空思考，动作返回全部内容。

        参数:
            content: 原始响应内容。

        返回:
            (thinking, action) 元组。
        """
        # 规则 1：检查 finish(message=
        if "finish(message=" in content:
            parts = content.split("finish(message=", 1)
            thinking = parts[0].strip()
            action = "finish(message=" + parts[1]
            return thinking, action

        # 规则 2：检查 do(action=
        if "do(action=" in content:
            parts = content.split("do(action=", 1)
            thinking = parts[0].strip()
            action = "do(action=" + parts[1]
            return thinking, action

        # 规则 3：回退到旧式 XML 标签解析
        if "<answer>" in content:
            parts = content.split("<answer>", 1)
            thinking = parts[0].replace("<think>", "").replace("</think>", "").strip()
            action = parts[1].replace("</answer>", "").strip()
            return thinking, action

        # 规则 4：未找到标记，动作直接返回内容
        return "", content


class MessageBuilder:
    """构建对话消息的辅助类。"""

    @staticmethod
    def create_system_message(content: str) -> dict[str, Any]:
        """创建系统消息。"""
        return {"role": "system", "content": content}

    @staticmethod
    def create_user_message(
        text: str, image_base64: str | None = None
    ) -> dict[str, Any]:
        """
        创建用户消息，可选附带图片。

        参数:
            text: 文本内容。
            image_base64: 可选的 base64 编码图片。

        返回:
            消息字典。
        """
        content = []

        if image_base64:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{image_base64}"},
                }
            )

        content.append({"type": "text", "text": text})

        return {"role": "user", "content": content}

    @staticmethod
    def create_assistant_message(content: str) -> dict[str, Any]:
        """创建助手消息。"""
        return {"role": "assistant", "content": content}

    @staticmethod
    def remove_images_from_message(message: dict[str, Any]) -> dict[str, Any]:
        """
        移除消息中的图片内容以节省上下文空间。

        参数:
            message: 消息字典。

        返回:
            已移除图片的消息。
        """
        if isinstance(message.get("content"), list):
            message["content"] = [
                item for item in message["content"] if item.get("type") == "text"
            ]
        return message

    @staticmethod
    def build_screen_info(current_app: str, **extra_info) -> str:
        """
        为模型构建屏幕信息字符串。

        参数:
            current_app: 当前应用名称。
            **extra_info: 需要附加的额外信息。

        返回:
            包含屏幕信息的 JSON 字符串。
        """
        info = {"current_app": current_app, **extra_info}
        return json.dumps(info, ensure_ascii=False)

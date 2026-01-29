"""用于编排 iOS 手机自动化的 PhoneAgent 类。"""

import json
import traceback
from dataclasses import dataclass
from typing import Any, Callable

from phone_agent.actions.handler import do, finish, parse_action
from phone_agent.actions.handler_ios import IOSActionHandler
from phone_agent.config import get_messages, get_system_prompt
from phone_agent.model import ModelClient, ModelConfig
from phone_agent.model.client import MessageBuilder
from phone_agent.xctest import XCTestConnection, get_current_app, get_screenshot


@dataclass
class IOSAgentConfig:
    """iOS PhoneAgent 的配置。"""

    max_steps: int = 100
    wda_url: str = "http://localhost:8100"
    session_id: str | None = None
    device_id: str | None = None  # iOS 设备 UDID
    lang: str = "cn"
    system_prompt: str | None = None
    verbose: bool = True

    def __post_init__(self):
        """补齐系统提示词的默认值。"""
        # 关键步骤：补齐系统提示词，确保首轮提示内容完整
        if self.system_prompt is None:
            self.system_prompt = get_system_prompt(self.lang)


@dataclass
class StepResult:
    """单步执行结果。"""

    success: bool
    finished: bool
    action: dict[str, Any] | None
    thinking: str
    message: str | None = None


class IOSPhoneAgent:
    """
    用于自动化 iOS 手机交互的 AI Agent。

    Agent 使用视觉语言模型理解屏幕内容，并通过 WebDriverAgent 决定动作完成任务。

    参数:
        model_config: AI 模型配置。
        agent_config: iOS Agent 行为配置。
        confirmation_callback: 可选的敏感操作确认回调。
        takeover_callback: 可选的接管请求回调。

    示例:
        >>> from phone_agent.agent_ios import IOSPhoneAgent, IOSAgentConfig
        >>> from phone_agent.model import ModelConfig
        >>>
        >>> model_config = ModelConfig(base_url="http://localhost:8000/v1")
        >>> agent_config = IOSAgentConfig(wda_url="http://localhost:8100")
        >>> agent = IOSPhoneAgent(model_config, agent_config)
        >>> agent.run("Open Safari and search for Apple")
    """

    def __init__(
        self,
        model_config: ModelConfig | None = None,
        agent_config: IOSAgentConfig | None = None,
        confirmation_callback: Callable[[str], bool] | None = None,
        takeover_callback: Callable[[str], None] | None = None,
    ):
        """初始化 iOS Agent，建立模型与 WDA 控制链路。"""
        # 关键步骤：初始化模型客户端、WDA 连接与动作执行器
        self.model_config = model_config or ModelConfig()
        self.agent_config = agent_config or IOSAgentConfig()

        self.model_client = ModelClient(self.model_config)

        # 初始化 WDA 连接，并在需要时创建会话
        self.wda_connection = XCTestConnection(wda_url=self.agent_config.wda_url)

        # 未提供会话时自动创建
        if self.agent_config.session_id is None:
            success, session_id = self.wda_connection.start_wda_session()
            if success and session_id != "session_started":
                self.agent_config.session_id = session_id
                if self.agent_config.verbose:
                    print(f"✅ Created WDA session: {session_id}")
            elif self.agent_config.verbose:
                print(f"⚠️  Using default WDA session (no explicit session ID)")

        self.action_handler = IOSActionHandler(
            wda_url=self.agent_config.wda_url,
            session_id=self.agent_config.session_id,
            confirmation_callback=confirmation_callback,
            takeover_callback=takeover_callback,
        )

        self._context: list[dict[str, Any]] = []
        self._step_count = 0

    def run(self, task: str) -> str:
        """
        运行 Agent 以完成任务。

        参数:
            task: 任务的自然语言描述。

        返回:
            Agent 的最终消息。
        """
        # 关键步骤：重置上下文并启动主执行循环
        self._context = []
        self._step_count = 0

        # 首次步骤包含用户提示
        result = self._execute_step(task, is_first=True)

        if result.finished:
            return result.message or "Task completed"

        # 继续执行直到完成或达到最大步数
        while self._step_count < self.agent_config.max_steps:
            result = self._execute_step(is_first=False)

            if result.finished:
                return result.message or "Task completed"

        return "Max steps reached"

    def step(self, task: str | None = None) -> StepResult:
        """
        执行 Agent 的单步。

        适用于手动控制或调试。

        参数:
            task: 任务描述（仅首步需要）。

        返回:
            包含步骤详情的 StepResult。
        """
        # 关键步骤：校验首步输入并执行单步推理
        is_first = len(self._context) == 0

        if is_first and not task:
            raise ValueError("Task is required for the first step")

        return self._execute_step(task, is_first)

    def reset(self) -> None:
        """为新任务重置 Agent 状态。"""
        # 关键步骤：清空上下文与步数计数，准备新任务
        self._context = []
        self._step_count = 0

    def _execute_step(
        self, user_prompt: str | None = None, is_first: bool = False
    ) -> StepResult:
        """执行 Agent 循环中的单步。"""
        # 关键步骤：采集屏幕与当前应用，调用模型并执行动作
        self._step_count += 1

        # 获取当前屏幕状态
        screenshot = get_screenshot(
            wda_url=self.agent_config.wda_url,
            session_id=self.agent_config.session_id,
            device_id=self.agent_config.device_id,
        )
        current_app = get_current_app(
            wda_url=self.agent_config.wda_url, session_id=self.agent_config.session_id
        )

        # 构建消息
        if is_first:
            self._context.append(
                MessageBuilder.create_system_message(self.agent_config.system_prompt)
            )

            screen_info = MessageBuilder.build_screen_info(current_app)
            text_content = f"{user_prompt}\n\n{screen_info}"

            self._context.append(
                MessageBuilder.create_user_message(
                    text=text_content, image_base64=screenshot.base64_data
                )
            )
        else:
            screen_info = MessageBuilder.build_screen_info(current_app)
            text_content = f"** Screen Info **\n\n{screen_info}"

            self._context.append(
                MessageBuilder.create_user_message(
                    text=text_content, image_base64=screenshot.base64_data
                )
            )

        # 获取模型响应
        try:
            response = self.model_client.request(self._context)
        except Exception as e:
            if self.agent_config.verbose:
                traceback.print_exc()
            return StepResult(
                success=False,
                finished=True,
                action=None,
                thinking="",
                message=f"Model error: {e}",
            )

        # 解析响应中的动作
        try:
            action = parse_action(response.action)
        except ValueError:
            if self.agent_config.verbose:
                traceback.print_exc()
            action = finish(message=response.action)

        if self.agent_config.verbose:
            # 输出思考过程
            msgs = get_messages(self.agent_config.lang)
            print("\n" + "=" * 50)
            print(f"💭 {msgs['thinking']}:")
            print("-" * 50)
            print(response.thinking)
            print("-" * 50)
            print(f"🎯 {msgs['action']}:")
            print(json.dumps(action, ensure_ascii=False, indent=2))
            print("=" * 50 + "\n")

        # 移除上下文中的图片以节省空间
        self._context[-1] = MessageBuilder.remove_images_from_message(self._context[-1])

        # 执行动作
        try:
            result = self.action_handler.execute(
                action, screenshot.width, screenshot.height
            )
        except Exception as e:
            if self.agent_config.verbose:
                traceback.print_exc()
            result = self.action_handler.execute(
                finish(message=str(e)), screenshot.width, screenshot.height
            )

        # 将助手响应加入上下文
        self._context.append(
            MessageBuilder.create_assistant_message(
                f"<think>{response.thinking}</think><answer>{response.action}</answer>"
            )
        )

        # 检查是否完成
        finished = action.get("_metadata") == "finish" or result.should_finish

        if finished and self.agent_config.verbose:
            msgs = get_messages(self.agent_config.lang)
            print("\n" + "🎉 " + "=" * 48)
            print(
                f"✅ {msgs['task_completed']}: {result.message or action.get('message', msgs['done'])}"
            )
            print("=" * 50 + "\n")

        return StepResult(
            success=result.success,
            finished=finished,
            action=action,
            thinking=response.thinking,
            message=result.message or action.get("message"),
        )

    @property
    def context(self) -> list[dict[str, Any]]:
        """获取当前对话上下文。"""
        # 关键步骤：返回上下文副本，避免外部直接修改
        return self._context.copy()

    @property
    def step_count(self) -> int:
        """获取当前步骤计数。"""
        # 关键步骤：返回当前步数，便于调试与限步控制
        return self._step_count

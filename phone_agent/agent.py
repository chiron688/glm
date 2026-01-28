"""用于编排手机自动化的主 PhoneAgent 类。"""

import json
import traceback
from dataclasses import dataclass
from typing import Any, Callable

from phone_agent.actions import ActionHandler
from phone_agent.actions.handler import do, finish, parse_action
from phone_agent.config import get_messages, get_system_prompt
from phone_agent.device_factory import get_device_factory
from phone_agent.model import ModelClient, ModelConfig
from phone_agent.model.client import MessageBuilder
from phone_agent.skills import (
    SkillRegistry,
    SkillRunner,
    SkillRunnerConfig,
    SkillRouter,
    SkillRouterConfig,
)


@dataclass
class AgentConfig:
    """PhoneAgent 的配置。"""

    max_steps: int = 100
    device_id: str | None = None
    lang: str = "cn"
    system_prompt: str | None = None
    verbose: bool = True
    skill_paths: list[str] | None = None
    enable_skill_routing: bool = False
    skill_fallback_to_model: bool = True
    skill_common_handlers_path: str | None = None
    skill_record_dir: str | None = None
    skill_playback_dir: str | None = None

    def __post_init__(self):
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


class PhoneAgent:
    """
    用于自动化 Android 手机交互的 AI Agent。

    Agent 使用视觉语言模型理解屏幕内容，并决定动作来完成用户任务。

    参数:
        model_config: AI 模型配置。
        agent_config: Agent 行为配置。
        confirmation_callback: 可选的敏感操作确认回调。
        takeover_callback: 可选的接管请求回调。

    示例:
        >>> from phone_agent import PhoneAgent
        >>> from phone_agent.model import ModelConfig
        >>>
        >>> model_config = ModelConfig(base_url="http://localhost:8000/v1")
        >>> agent = PhoneAgent(model_config)
        >>> agent.run("Open WeChat and send a message to John")
    """

    def __init__(
        self,
        model_config: ModelConfig | None = None,
        agent_config: AgentConfig | None = None,
        confirmation_callback: Callable[[str], bool] | None = None,
        takeover_callback: Callable[[str], None] | None = None,
        skill_registry: SkillRegistry | None = None,
        skill_runner_config: SkillRunnerConfig | None = None,
        skill_router: SkillRouter | None = None,
    ):
        self.model_config = model_config or ModelConfig()
        self.agent_config = agent_config or AgentConfig()

        self.model_client = ModelClient(self.model_config)
        self.action_handler = ActionHandler(
            device_id=self.agent_config.device_id,
            confirmation_callback=confirmation_callback,
            takeover_callback=takeover_callback,
        )

        self.skill_registry = skill_registry
        if self.skill_registry is None and self.agent_config.skill_paths:
            registry = SkillRegistry()
            registry.load_from_paths(self.agent_config.skill_paths)
            self.skill_registry = registry

        self.skill_runner = None
        if self.skill_registry is not None:
            runner_config = skill_runner_config or SkillRunnerConfig(
                common_error_handlers_path=self.agent_config.skill_common_handlers_path,
                record_dir=self.agent_config.skill_record_dir,
                playback_dir=self.agent_config.skill_playback_dir,
            )
            self.skill_runner = SkillRunner(
                self.skill_registry,
                config=runner_config,
                device_id=self.agent_config.device_id,
                action_handler=self.action_handler,
            )

        self.skill_router = skill_router
        if self.skill_router is None and self.skill_registry is not None:
            self.skill_router = SkillRouter(self.skill_registry, SkillRouterConfig())

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
        self._context = []
        self._step_count = 0

        # Skills routing (high-risk tasks prioritized)
        skill_result = self._try_run_skill(task)
        if skill_result is not None:
            if skill_result.success or not self.agent_config.skill_fallback_to_model:
                return skill_result.message

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
        is_first = len(self._context) == 0

        if is_first and not task:
            raise ValueError("Task is required for the first step")

        return self._execute_step(task, is_first)

    def reset(self) -> None:
        """为新任务重置 Agent 状态。"""
        self._context = []
        self._step_count = 0

    def _try_run_skill(self, task: str):
        if not self.agent_config.enable_skill_routing:
            return None
        if self.skill_registry is None or self.skill_runner is None or self.skill_router is None:
            return None
        try:
            observation = self.skill_runner.observer.capture()
        except Exception:
            observation = None
        decision = self.skill_router.select(task, observation)
        if decision is None:
            return None
        if self.agent_config.verbose:
            print(f"🧭 Skill routing to '{decision.skill_id}' ({decision.reason})")
        return self.skill_runner.run(decision.skill_id, decision.inputs)

    def _execute_step(
        self, user_prompt: str | None = None, is_first: bool = False
    ) -> StepResult:
        """执行 Agent 循环中的单步。"""
        self._step_count += 1

        # 获取当前屏幕状态
        device_factory = get_device_factory()
        screenshot = device_factory.get_screenshot(self.agent_config.device_id)
        current_app = device_factory.get_current_app(self.agent_config.device_id)

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
            msgs = get_messages(self.agent_config.lang)
            print("\n" + "=" * 50)
            print(f"💭 {msgs['thinking']}:")
            print("-" * 50)
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
        return self._context.copy()

    @property
    def step_count(self) -> int:
        """获取当前步骤计数。"""
        return self._step_count

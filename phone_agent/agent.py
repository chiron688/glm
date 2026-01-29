"""用于编排手机自动化的主 PhoneAgent 类。"""

import json
import time
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
    SkillError,
    SkillErrorCode,
    SkillRegistry,
    SkillRunResult,
    SkillRunner,
    SkillRunnerConfig,
    SkillRouter,
    SkillRouterConfig,
)
from phone_agent.skills.reporting import SkillRunReport


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
    skill_whitelist: list[str] | None = None
    skill_risk_gate_enabled: bool = False
    skill_risk_keywords: list[str] | None = None

    def __post_init__(self):
        """补齐系统提示词与风险关键词的默认值。"""
        # 关键步骤：补齐系统提示词与风险关键词，确保技能路由的安全策略可用
        if self.system_prompt is None:
            self.system_prompt = get_system_prompt(self.lang)
        if self.skill_risk_keywords is None:
            self.skill_risk_keywords = ["发布", "上传", "post", "upload", "publish"]


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
        """初始化 PhoneAgent 并装配模型、动作处理器与技能组件。"""
        # 关键步骤：初始化模型客户端、动作执行器与技能路由/执行组件
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
            router_config = SkillRouterConfig(
                enforce_skill_whitelist=bool(self.agent_config.skill_whitelist),
                skill_whitelist=self.agent_config.skill_whitelist or [],
                enforce_on_risk=self.agent_config.skill_risk_gate_enabled,
                risk_keywords=self.agent_config.skill_risk_keywords or [],
            )
            self.skill_router = SkillRouter(self.skill_registry, router_config)

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
        # 关键步骤：重置上下文并驱动技能路由与主执行循环
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

    def _try_run_skill(self, task: str):
        """根据路由策略尝试执行技能或阻断高风险任务。"""
        # 关键步骤：根据路由决策执行技能、阻断风险或跳过影子技能
        if not self.agent_config.enable_skill_routing:
            return None
        if self.skill_registry is None or self.skill_runner is None or self.skill_router is None:
            return None
        try:
            observation = self.skill_runner.observer.capture()
        except Exception:
            observation = None
        decision = self.skill_router.select(task, observation)
        if decision.action == "block":
            now = 0.0
            try:
                now = time.time()
            except Exception:
                now = 0.0
            report = SkillRunReport(
                skill_id="__blocked__",
                started_at=now,
                ended_at=now,
                inputs={"reason": decision.reason},
            )
            error = SkillError(
                code=SkillErrorCode.ABORTED,
                message="Blocked by risk gate",
                stage="routing",
            )
            return SkillRunResult(
                success=True,
                message=f"Blocked by risk gate: {decision.reason}",
                error=error,
                report=report,
            )
        if decision.action == "none":
            return None
        if decision.action == "shadow":
            if self.agent_config.verbose and decision.directive:
                print(f"🧭 Shadow skill matched '{decision.directive.skill_id}', skipping execution")
            return None
        if self.agent_config.verbose:
            print(f"🧭 Skill routing to '{decision.directive.skill_id}' ({decision.reason})")
        return self.skill_runner.run(decision.directive.skill_id, decision.directive.inputs)

    def _execute_step(
        self, user_prompt: str | None = None, is_first: bool = False
    ) -> StepResult:
        """执行 Agent 循环中的单步。"""
        # 关键步骤：采集屏幕、请求模型、解析动作并执行
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
        # 关键步骤：返回上下文副本，避免外部直接修改
        return self._context.copy()

    @property
    def step_count(self) -> int:
        """获取当前步骤计数。"""
        # 关键步骤：返回当前步数，便于调试与限步控制
        return self._step_count

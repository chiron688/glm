"""使用 WebDriverAgent 的 iOS 自动化动作处理器。"""

import time
from dataclasses import dataclass
from typing import Any, Callable

from phone_agent.xctest import (
    back,
    double_tap,
    home,
    launch_app,
    long_press,
    swipe,
    tap,
)
from phone_agent.xctest.input import clear_text, hide_keyboard, type_text


@dataclass
class ActionResult:
    """动作执行结果。"""

    success: bool
    should_finish: bool
    message: str | None = None
    requires_confirmation: bool = False


class IOSActionHandler:
    """
    处理 iOS 设备上来自 AI 模型输出的动作执行。

    参数:
        wda_url: WebDriverAgent 地址。
        session_id: 可选的 WDA 会话 ID。
        confirmation_callback: 可选的敏感操作确认回调。
            返回 True 继续，False 取消。
        takeover_callback: 可选的接管请求回调（登录、验证码等）。
    """

    def __init__(
        self,
        wda_url: str = "http://localhost:8100",
        session_id: str | None = None,
        confirmation_callback: Callable[[str], bool] | None = None,
        takeover_callback: Callable[[str], None] | None = None,
    ):
        """初始化 iOS 动作处理器，配置 WDA 与回调函数。"""
        # 关键步骤：初始化 iOS 动作处理器，配置 WDA 与回调函数
        self.wda_url = wda_url
        self.session_id = session_id
        self.confirmation_callback = confirmation_callback or self._default_confirmation
        self.takeover_callback = takeover_callback or self._default_takeover

    def execute(
        self, action: dict[str, Any], screen_width: int, screen_height: int
    ) -> ActionResult:
        """
        执行来自 AI 模型的动作。

        参数:
            action: 模型输出的动作字典。
            screen_width: 当前屏幕宽度（像素）。
            screen_height: 当前屏幕高度（像素）。

        返回:
            ActionResult，表示是否成功以及是否结束。
        """
        # 关键步骤：解析动作类型并分派到 iOS 处理器执行
        action_type = action.get("_metadata")

        if action_type == "finish":
            return ActionResult(
                success=True, should_finish=True, message=action.get("message")
            )

        if action_type != "do":
            return ActionResult(
                success=False,
                should_finish=True,
                message=f"Unknown action type: {action_type}",
            )

        action_name = action.get("action")
        handler_method = self._get_handler(action_name)

        if handler_method is None:
            return ActionResult(
                success=False,
                should_finish=False,
                message=f"Unknown action: {action_name}",
            )

        try:
            return handler_method(action, screen_width, screen_height)
        except Exception as e:
            return ActionResult(
                success=False, should_finish=False, message=f"Action failed: {e}"
            )

    def _get_handler(self, action_name: str) -> Callable | None:
        """获取指定动作的处理方法。"""
        # 关键步骤：根据动作名称返回处理函数
        handlers = {
            "Launch": self._handle_launch,
            "Tap": self._handle_tap,
            "Type": self._handle_type,
            "Type_Name": self._handle_type,
            "Swipe": self._handle_swipe,
            "Back": self._handle_back,
            "Home": self._handle_home,
            "Double Tap": self._handle_double_tap,
            "Long Press": self._handle_long_press,
            "Wait": self._handle_wait,
            "Take_over": self._handle_takeover,
            "Note": self._handle_note,
            "Call_API": self._handle_call_api,
            "Interact": self._handle_interact,
        }
        return handlers.get(action_name)

    def _convert_relative_to_absolute(
        self, element: list[int], screen_width: int, screen_height: int
    ) -> tuple[int, int]:
        """将相对坐标（0-1000）转换为绝对像素。"""
        # 关键步骤：将 0-1000 的相对坐标转换为像素坐标
        x = int(element[0] / 1000 * screen_width)
        y = int(element[1] / 1000 * screen_height)
        return x, y

    def _handle_launch(self, action: dict, width: int, height: int) -> ActionResult:
        """处理应用启动动作。"""
        # 关键步骤：启动指定应用并返回执行结果
        app_name = action.get("app")
        if not app_name:
            return ActionResult(False, False, "No app name specified")

        success = launch_app(
            app_name, wda_url=self.wda_url, session_id=self.session_id
        )
        if success:
            return ActionResult(True, False)
        return ActionResult(False, False, f"App not found: {app_name}")

    def _handle_tap(self, action: dict, width: int, height: int) -> ActionResult:
        """处理点击动作。"""
        # 关键步骤：执行点击动作，并在必要时触发敏感确认
        element = action.get("element")
        if not element:
            return ActionResult(False, False, "No element coordinates")

        x, y = self._convert_relative_to_absolute(element, width, height)

        print(f"Physically tap on ({x}, {y})")

        # 检查是否为敏感操作
        if "message" in action:
            if not self.confirmation_callback(action["message"]):
                return ActionResult(
                    success=False,
                    should_finish=True,
                    message="User cancelled sensitive operation",
                )

        tap(x, y, wda_url=self.wda_url, session_id=self.session_id)
        return ActionResult(True, False)

    def _handle_type(self, action: dict, width: int, height: int) -> ActionResult:
        """处理文本输入动作。"""
        # 关键步骤：输入文本内容
        text = action.get("text", "")

        # 清空已有文本并输入新文本
        clear_text(wda_url=self.wda_url, session_id=self.session_id)
        time.sleep(0.5)

        type_text(text, wda_url=self.wda_url, session_id=self.session_id)
        time.sleep(0.5)

        # 输入完成后隐藏键盘
        hide_keyboard(wda_url=self.wda_url, session_id=self.session_id)
        time.sleep(0.5)

        return ActionResult(True, False)

    def _handle_swipe(self, action: dict, width: int, height: int) -> ActionResult:
        """处理滑动动作。"""
        # 关键步骤：执行滑动动作并支持设置时长
        start = action.get("start")
        end = action.get("end")

        if not start or not end:
            return ActionResult(False, False, "Missing swipe coordinates")

        start_x, start_y = self._convert_relative_to_absolute(start, width, height)
        end_x, end_y = self._convert_relative_to_absolute(end, width, height)

        print(f"Physically scroll from ({start_x}, {start_y}) to ({end_x}, {end_y})")

        swipe(
            start_x,
            start_y,
            end_x,
            end_y,
            wda_url=self.wda_url,
            session_id=self.session_id,
        )
        return ActionResult(True, False)

    def _handle_back(self, action: dict, width: int, height: int) -> ActionResult:
        """处理返回手势（从左边缘滑动）。"""
        # 关键步骤：发送返回键事件
        back(wda_url=self.wda_url, session_id=self.session_id)
        return ActionResult(True, False)

    def _handle_home(self, action: dict, width: int, height: int) -> ActionResult:
        """处理 Home 按钮动作。"""
        # 关键步骤：发送主页键事件
        home(wda_url=self.wda_url, session_id=self.session_id)
        return ActionResult(True, False)

    def _handle_double_tap(self, action: dict, width: int, height: int) -> ActionResult:
        """处理双击动作。"""
        # 关键步骤：执行双击动作
        element = action.get("element")
        if not element:
            return ActionResult(False, False, "No element coordinates")

        x, y = self._convert_relative_to_absolute(element, width, height)
        double_tap(x, y, wda_url=self.wda_url, session_id=self.session_id)
        return ActionResult(True, False)

    def _handle_long_press(self, action: dict, width: int, height: int) -> ActionResult:
        """处理长按动作。"""
        # 关键步骤：执行长按动作并支持时长
        element = action.get("element")
        if not element:
            return ActionResult(False, False, "No element coordinates")

        x, y = self._convert_relative_to_absolute(element, width, height)
        long_press(
            x,
            y,
            duration=3.0,
            wda_url=self.wda_url,
            session_id=self.session_id,
        )
        return ActionResult(True, False)

    def _handle_wait(self, action: dict, width: int, height: int) -> ActionResult:
        """处理等待动作。"""
        # 关键步骤：等待指定时长以保持节奏
        duration_str = action.get("duration", "1 seconds")
        try:
            duration = float(duration_str.replace("seconds", "").strip())
        except ValueError:
            duration = 1.0

        time.sleep(duration)
        return ActionResult(True, False)

    def _handle_takeover(self, action: dict, width: int, height: int) -> ActionResult:
        """处理接管请求（登录、验证码等）。"""
        # 关键步骤：触发人工接管回调
        message = action.get("message", "User intervention required")
        self.takeover_callback(message)
        return ActionResult(True, False)

    def _handle_note(self, action: dict, width: int, height: int) -> ActionResult:
        """处理 Note 动作（内容记录的占位实现）。"""
        # 关键步骤：处理备注动作（占位实现）
        # 该动作通常用于记录页面内容
        # 具体实现取决于实际需求
        return ActionResult(True, False)

    def _handle_call_api(self, action: dict, width: int, height: int) -> ActionResult:
        """处理 API 调用动作（摘要的占位实现）。"""
        # 关键步骤：处理外部 API 调用动作（占位实现）
        # 该动作通常用于内容摘要
        # 具体实现取决于实际需求
        return ActionResult(True, False)

    def _handle_interact(self, action: dict, width: int, height: int) -> ActionResult:
        """处理交互请求（需要用户选择）。"""
        # 关键步骤：处理需要用户交互的动作
        # 该动作表示需要用户输入
        return ActionResult(True, False, message="User interaction required")

    @staticmethod
    def _default_confirmation(message: str) -> bool:
        """使用控制台输入的默认确认回调。"""
        # 关键步骤：默认敏感操作确认回调（控制台输入）
        response = input(f"Sensitive operation: {message}\nConfirm? (Y/N): ")
        return response.upper() == "Y"

    @staticmethod
    def _default_takeover(message: str) -> None:
        """使用控制台输入的默认接管回调。"""
        # 关键步骤：默认人工接管回调（控制台等待）
        input(f"{message}\nPress Enter after completing manual operation...")

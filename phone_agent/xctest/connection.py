"""通过 idevice 工具与 WebDriverAgent 管理 iOS 设备连接。"""

import subprocess
import time
from dataclasses import dataclass
from enum import Enum


class ConnectionType(Enum):
    """iOS 连接类型。"""

    USB = "usb"
    NETWORK = "network"


@dataclass
class DeviceInfo:
    """连接的 iOS 设备信息。"""

    device_id: str  # 设备 UDID
    status: str
    connection_type: ConnectionType
    model: str | None = None
    ios_version: str | None = None
    device_name: str | None = None


class XCTestConnection:
    """
    通过 libimobiledevice 与 WebDriverAgent 管理 iOS 设备连接。

    依赖:
        - libimobiledevice（idevice_id, ideviceinfo）
        - iOS 设备上运行的 WebDriverAgent
        - ios-deploy（可选，用于应用安装）

    示例:
        >>> conn = XCTestConnection()
        >>> # 列出已连接的设备
        >>> devices = conn.list_devices()
        >>> # 获取设备信息
        >>> info = conn.get_device_info()
        >>> # 检查 WDA 是否运行
        >>> is_ready = conn.is_wda_ready()
    """

    def __init__(self, wda_url: str = "http://localhost:8100"):
        """
        初始化 iOS 连接管理器。

        参数:
            wda_url: WebDriverAgent 地址（默认: http://localhost:8100）。
                     网络设备使用 http://<device-ip>:8100
        """
        # 关键步骤：初始化XCTestConnection，配置iOS 连接所需的参数与依赖
        self.wda_url = wda_url.rstrip("/")

    def list_devices(self) -> list[DeviceInfo]:
        """
        列出所有已连接的 iOS 设备。

        返回:
            DeviceInfo 对象列表。

        说明:
            需要安装 libimobiledevice。
            macOS 安装: brew install libimobiledevice
        """
        # 关键步骤：列出已连接的 iOS 设备
        try:
            # 获取设备 UDID 列表
            result = subprocess.run(
                ["idevice_id", "-ln"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            devices = []
            for line in result.stdout.strip().split("\n"):
                udid = line.strip()
                if not udid:
                    continue

                # 判断连接类型（网络设备 UDID 有特定格式）
                conn_type = (
                    ConnectionType.NETWORK
                    if "-" in udid and len(udid) > 40
                    else ConnectionType.USB
                )

                # 获取设备详细信息
                device_info = self._get_device_details(udid)

                devices.append(
                    DeviceInfo(
                        device_id=udid,
                        status="connected",
                        connection_type=conn_type,
                        model=device_info.get("model"),
                        ios_version=device_info.get("ios_version"),
                        device_name=device_info.get("name"),
                    )
                )

            return devices

        except FileNotFoundError:
            print(
                "Error: idevice_id not found. Install libimobiledevice: brew install libimobiledevice"
            )
            return []
        except Exception as e:
            print(f"Error listing devices: {e}")
            return []

    def _get_device_details(self, udid: str) -> dict[str, str]:
        """
        获取指定设备的详细信息。

        参数:
            udid: 设备 UDID。

        返回:
            设备详情字典。
        """
        # 关键步骤：查询设备详细信息（型号、系统版本等）
        try:
            result = subprocess.run(
                ["ideviceinfo", "-u", udid],
                capture_output=True,
                text=True,
                timeout=5,
            )

            info = {}
            for line in result.stdout.split("\n"):
                if ": " in line:
                    key, value = line.split(": ", 1)
                    key = key.strip()
                    value = value.strip()

                    if key == "ProductType":
                        info["model"] = value
                    elif key == "ProductVersion":
                        info["ios_version"] = value
                    elif key == "DeviceName":
                        info["name"] = value

            return info

        except Exception:
            return {}

    def get_device_info(self, device_id: str | None = None) -> DeviceInfo | None:
        """
        获取设备的详细信息。

        参数:
            device_id: 设备 UDID。为 None 时使用第一个可用设备。

        返回:
            DeviceInfo 对象，未找到则返回 None。
        """
        # 关键步骤：获取设备的基础信息
        devices = self.list_devices()

        if not devices:
            return None

        if device_id is None:
            return devices[0]

        for device in devices:
            if device.device_id == device_id:
                return device

        return None

    def is_connected(self, device_id: str | None = None) -> bool:
        """
        检查设备是否已连接。

        参数:
            device_id: 要检查的设备 UDID。为 None 时检查是否有任意设备连接。

        返回:
            已连接返回 True，否则返回 False。
        """
        # 关键步骤：检查设备是否已连接
        devices = self.list_devices()

        if not devices:
            return False

        if device_id is None:
            return len(devices) > 0

        return any(d.device_id == device_id for d in devices)

    def is_wda_ready(self, timeout: int = 2) -> bool:
        """
        检查 WebDriverAgent 是否运行且可访问。

        参数:
            timeout: 请求超时时间（秒）。

        返回:
            WDA 可用返回 True，否则返回 False。
        """
        # 关键步骤：检查 WDA 服务是否可用
        try:
            import requests

            response = requests.get(
                f"{self.wda_url}/status", timeout=timeout, verify=False
            )
            return response.status_code == 200
        except ImportError:
            print(
                "Error: requests library not found. Install it: pip install requests"
            )
            return False
        except Exception:
            return False

    def start_wda_session(self) -> tuple[bool, str]:
        """
        启动新的 WebDriverAgent 会话。

        返回:
            (success, session_id 或 error_message) 的元组。
        """
        # 关键步骤：启动 WDA 会话
        try:
            import requests

            response = requests.post(
                f"{self.wda_url}/session",
                json={"capabilities": {}},
                timeout=30,
                verify=False,
            )

            if response.status_code in (200, 201):
                data = response.json()
                session_id = data.get("sessionId") or data.get("value", {}).get(
                    "sessionId"
                )
                return True, session_id or "session_started"
            else:
                return False, f"Failed to start session: {response.text}"

        except ImportError:
            return (
                False,
                "requests library not found. Install it: pip install requests",
            )
        except Exception as e:
            return False, f"Error starting WDA session: {e}"

    def get_wda_status(self) -> dict | None:
        """
        获取 WebDriverAgent 状态信息。

        返回:
            状态字典，若不可用则返回 None。
        """
        # 关键步骤：获取 WDA 状态信息
        try:
            import requests

            response = requests.get(f"{self.wda_url}/status", timeout=5, verify=False)

            if response.status_code == 200:
                return response.json()
            return None

        except Exception:
            return None

    def pair_device(self, device_id: str | None = None) -> tuple[bool, str]:
        """
        与 iOS 设备配对（部分操作需要）。

        参数:
            device_id: 设备 UDID。为 None 时使用第一个可用设备。

        返回:
            (success, message) 的元组。
        """
        # 关键步骤：执行 iOS 设备配对
        try:
            cmd = ["idevicepair"]
            if device_id:
                cmd.extend(["-u", device_id])
            cmd.append("pair")

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            output = result.stdout + result.stderr

            if "SUCCESS" in output or "already paired" in output.lower():
                return True, "Device paired successfully"
            else:
                return False, output.strip()

        except FileNotFoundError:
            return (
                False,
                "idevicepair not found. Install libimobiledevice: brew install libimobiledevice",
            )
        except Exception as e:
            return False, f"Error pairing device: {e}"

    def get_device_name(self, device_id: str | None = None) -> str | None:
        """
        获取设备名称。

        参数:
            device_id: 设备 UDID。为 None 时使用第一个可用设备。

        返回:
            设备名称字符串，未找到则返回 None。
        """
        # 关键步骤：获取设备名称
        try:
            cmd = ["ideviceinfo"]
            if device_id:
                cmd.extend(["-u", device_id])
            cmd.extend(["-k", "DeviceName"])

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)

            return result.stdout.strip() or None

        except Exception as e:
            print(f"Error getting device name: {e}")
            return None

    def restart_wda(self) -> tuple[bool, str]:
        """
        重启 WebDriverAgent（需要在设备上手动重启）。

        返回:
            (success, message) 的元组。

        说明:
            该方法仅检查是否需要重启 WDA。
            实际重启需要通过 Xcode 或其他方式在设备上重新运行 WDA。
        """
        # 关键步骤：重启 WDA 服务
        if self.is_wda_ready():
            return True, "WDA is already running"
        else:
            return (
                False,
                "WDA is not running. Please start it manually on the device.",
            )


def quick_connect(wda_url: str = "http://localhost:8100") -> tuple[bool, str]:
    """
    快速检查 iOS 设备连接与 WDA 状态的辅助方法。

    参数:
        wda_url: WebDriverAgent 地址。

    返回:
        (success, message) 的元组。
    """
    # 关键步骤：快速检查 WDA 连接状态
    conn = XCTestConnection(wda_url=wda_url)

    # 检查是否有设备连接
    if not conn.is_connected():
        return False, "No iOS device connected"

    # 检查 WDA 是否就绪
    if not conn.is_wda_ready():
        return False, "WebDriverAgent is not running"

    return True, "iOS device connected and WDA ready"


def list_devices() -> list[DeviceInfo]:
    """
    快速列出已连接的 iOS 设备。

    返回:
        DeviceInfo 对象列表。
    """
    # 关键步骤：列出已连接的 iOS 设备
    conn = XCTestConnection()
    return conn.list_devices()

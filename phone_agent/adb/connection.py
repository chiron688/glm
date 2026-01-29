"""本地与远程设备的 ADB 连接管理。"""

import subprocess
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from phone_agent.config.timing import TIMING_CONFIG


class ConnectionType(Enum):
    """ADB 连接类型。"""

    USB = "usb"
    WIFI = "wifi"
    REMOTE = "remote"


@dataclass
class DeviceInfo:
    """已连接设备信息。"""

    device_id: str
    status: str
    connection_type: ConnectionType
    model: str | None = None
    android_version: str | None = None


class ADBConnection:
    """
    管理 Android 设备的 ADB 连接。

    支持 USB、WiFi 和远程 TCP/IP 连接。

    示例:
        >>> conn = ADBConnection()
        >>> # 连接远程设备
        >>> conn.connect("192.168.1.100:5555")
        >>> # 列出设备
        >>> devices = conn.list_devices()
        >>> # 断开连接
        >>> conn.disconnect("192.168.1.100:5555")
    """

    def __init__(self, adb_path: str = "adb"):
        """
        初始化 ADB 连接管理器。

        参数:
            adb_path: ADB 可执行文件路径。
        """
        # 关键步骤：初始化ADBConnection，配置ADB 连接所需的参数与依赖
        self.adb_path = adb_path

    def connect(self, address: str, timeout: int = 10) -> tuple[bool, str]:
        """
        通过 TCP/IP 连接远程设备。

        参数:
            address: 设备地址，格式为 "host:port"（例如 "192.168.1.100:5555"）。
            timeout: 连接超时时间（秒）。

        返回:
            (success, message) 的元组。

        说明:
            远程设备需要开启 TCP/IP 调试。
            可在设备上执行: adb tcpip 5555
        """
        # 关键步骤：通过 TCP/IP 连接到指定设备地址
        # 校验地址格式
        if ":" not in address:
            address = f"{address}:5555"  # 默认 ADB 端口

        try:
            result = subprocess.run(
                [self.adb_path, "connect", address],
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            output = result.stdout + result.stderr

            if "connected" in output.lower():
                return True, f"Connected to {address}"
            elif "already connected" in output.lower():
                return True, f"Already connected to {address}"
            else:
                return False, output.strip()

        except subprocess.TimeoutExpired:
            return False, f"Connection timeout after {timeout}s"
        except Exception as e:
            return False, f"Connection error: {e}"

    def disconnect(self, address: str | None = None) -> tuple[bool, str]:
        """
        断开远程设备连接。

        参数:
            address: 要断开的设备地址。为 None 时断开全部。

        返回:
            (success, message) 的元组。
        """
        # 关键步骤：断开远程设备连接
        try:
            cmd = [self.adb_path, "disconnect"]
            if address:
                cmd.append(address)

            result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=5)

            output = result.stdout + result.stderr
            return True, output.strip() or "Disconnected"

        except Exception as e:
            return False, f"Disconnect error: {e}"

    def list_devices(self) -> list[DeviceInfo]:
        """
        列出所有已连接设备。

        返回:
            DeviceInfo 对象列表。
        """
        # 关键步骤：列出当前可用的 ADB 设备
        try:
            result = subprocess.run(
                [self.adb_path, "devices", "-l"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            devices = []
            for line in result.stdout.strip().split("\n")[1:]:  # 跳过表头
                if not line.strip():
                    continue

                parts = line.split()
                if len(parts) >= 2:
                    device_id = parts[0]
                    status = parts[1]

                    # 判断连接类型
                    if ":" in device_id:
                        conn_type = ConnectionType.REMOTE
                    elif "emulator" in device_id:
                        conn_type = ConnectionType.USB  # 模拟器通过 USB
                    else:
                        conn_type = ConnectionType.USB

                    # 解析额外信息
                    model = None
                    for part in parts[2:]:
                        if part.startswith("model:"):
                            model = part.split(":", 1)[1]
                            break

                    devices.append(
                        DeviceInfo(
                            device_id=device_id,
                            status=status,
                            connection_type=conn_type,
                            model=model,
                        )
                    )

            return devices

        except Exception as e:
            print(f"Error listing devices: {e}")
            return []

    def get_device_info(self, device_id: str | None = None) -> DeviceInfo | None:
        """
        获取设备的详细信息。

        参数:
            device_id: 设备 ID。为 None 时使用第一个可用设备。

        返回:
            DeviceInfo 对象，未找到则返回 None。
        """
        # 关键步骤：获取设备的基本信息与状态
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
            device_id: 要检查的设备 ID。为 None 时检查是否有任意设备连接。

        返回:
            已连接返回 True，否则返回 False。
        """
        # 关键步骤：检查设备是否已连接
        devices = self.list_devices()

        if not devices:
            return False

        if device_id is None:
            return any(d.status == "device" for d in devices)

        return any(d.device_id == device_id and d.status == "device" for d in devices)

    def enable_tcpip(
        self, port: int = 5555, device_id: str | None = None
    ) -> tuple[bool, str]:
        """
        在 USB 连接的设备上启用 TCP/IP 调试。

        这将允许后续通过无线连接设备。

        参数:
            port: ADB 的 TCP 端口（默认: 5555）。
            device_id: 设备 ID。为 None 时使用第一个可用设备。

        返回:
            (success, message) 的元组。

        说明:
            设备必须先通过 USB 连接。
            启用后可拔掉 USB，通过 WiFi 连接。
        """
        # 关键步骤：开启设备 TCP/IP 调试模式
        try:
            cmd = [self.adb_path]
            if device_id:
                cmd.extend(["-s", device_id])
            cmd.extend(["tcpip", str(port)])

            result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=10)

            output = result.stdout + result.stderr

            if "restarting" in output.lower() or result.returncode == 0:
                time.sleep(TIMING_CONFIG.connection.adb_restart_delay)
                return True, f"TCP/IP mode enabled on port {port}"
            else:
                return False, output.strip()

        except Exception as e:
            return False, f"Error enabling TCP/IP: {e}"

    def get_device_ip(self, device_id: str | None = None) -> str | None:
        """
        获取已连接设备的 IP 地址。

        参数:
            device_id: 设备 ID。为 None 时使用第一个可用设备。

        返回:
            IP 地址字符串，未找到则返回 None。
        """
        # 关键步骤：查询设备当前 IP 地址
        try:
            cmd = [self.adb_path]
            if device_id:
                cmd.extend(["-s", device_id])
            cmd.extend(["shell", "ip", "route"])

            result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=5)

            # 从路由输出中解析 IP
            for line in result.stdout.split("\n"):
                if "src" in line:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == "src" and i + 1 < len(parts):
                            return parts[i + 1]

            # 备用方案：尝试 wlan0 接口
            cmd[-1] = "ip addr show wlan0"
            result = subprocess.run(
                cmd[:-1] + ["shell", "ip", "addr", "show", "wlan0"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=5,
            )

            for line in result.stdout.split("\n"):
                if "inet " in line:
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        return parts[1].split("/")[0]

            return None

        except Exception as e:
            print(f"Error getting device IP: {e}")
            return None

    def restart_server(self) -> tuple[bool, str]:
        """
        重启 ADB 服务。

        返回:
            (success, message) 的元组。
        """
        # 关键步骤：重启 ADB 服务端
        try:
            # 终止服务
            subprocess.run(
                [self.adb_path, "kill-server"], capture_output=True, timeout=5
            )

            time.sleep(TIMING_CONFIG.connection.server_restart_delay)

            # 启动服务
            subprocess.run(
                [self.adb_path, "start-server"], capture_output=True, timeout=5
            )

            return True, "ADB server restarted"

        except Exception as e:
            return False, f"Error restarting server: {e}"


def quick_connect(address: str) -> tuple[bool, str]:
    """
    快速连接远程设备的辅助方法。

    参数:
        address: 设备地址（例如 "192.168.1.100" 或 "192.168.1.100:5555"）。

    返回:
        (success, message) 的元组。
    """
    # 关键步骤：快速连接到设备地址
    conn = ADBConnection()
    return conn.connect(address)


def list_devices() -> list[DeviceInfo]:
    """
    快速列出已连接设备的辅助方法。

    返回:
        DeviceInfo 对象列表。
    """
    # 关键步骤：列出当前可用的 ADB 设备
    conn = ADBConnection()
    return conn.list_devices()

"""HarmonyOS 设备的 HDC 连接管理。"""

import os
import subprocess
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from phone_agent.config.timing import TIMING_CONFIG


# 用于控制 HDC 命令输出的全局标志
_HDC_VERBOSE = os.getenv("HDC_VERBOSE", "false").lower() in ("true", "1", "yes")


def _run_hdc_command(cmd: list, **kwargs) -> subprocess.CompletedProcess:
    """
    执行 HDC 命令，可选打印详细日志。

    参数:
        cmd: 要执行的命令列表。
        **kwargs: subprocess.run 的额外参数。

    返回:
        CompletedProcess 结果。
    """
    # 关键步骤：处理HDCcommand
    if _HDC_VERBOSE:
        print(f"[HDC] Running command: {' '.join(cmd)}")

    result = subprocess.run(cmd, **kwargs)

    if _HDC_VERBOSE and result.returncode != 0:
        print(f"[HDC] Command failed with return code {result.returncode}")
        if hasattr(result, 'stderr') and result.stderr:
            print(f"[HDC] Error: {result.stderr}")

    return result


def set_hdc_verbose(verbose: bool):
    """全局设置 HDC 详细日志模式。"""
    # 关键步骤：设置HDCverbose
    global _HDC_VERBOSE
    _HDC_VERBOSE = verbose


class ConnectionType(Enum):
    """HDC 连接类型。"""

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
    harmony_version: str | None = None


class HDCConnection:
    """
    管理 HarmonyOS 设备的 HDC 连接。

    支持 USB、WiFi 和远程 TCP/IP 连接。

    示例:
        >>> conn = HDCConnection()
        >>> # 连接远程设备
        >>> conn.connect("192.168.1.100:5555")
        >>> # 列出设备
        >>> devices = conn.list_devices()
        >>> # 断开连接
        >>> conn.disconnect("192.168.1.100:5555")
    """

    def __init__(self, hdc_path: str = "hdc"):
        """
        初始化 HDC 连接管理器。

        参数:
            hdc_path: HDC 可执行文件路径。
        """
        # 关键步骤：初始化HDCConnection，配置HDC 连接所需的参数与依赖
        self.hdc_path = hdc_path

    def connect(self, address: str, timeout: int = 10) -> tuple[bool, str]:
        """
        通过 TCP/IP 连接远程设备。

        参数:
            address: 设备地址，格式为 "host:port"（例如 "192.168.1.100:5555"）。
            timeout: 连接超时时间（秒）。

        返回:
            (success, message) 的元组。

        说明:
            远程设备需开启 TCP/IP 调试。
        """
        # 关键步骤：通过 TCP/IP 连接到指定设备地址
        # 校验地址格式
        if ":" not in address:
            address = f"{address}:5555"  # 默认 HDC 端口

        try:
            result = _run_hdc_command(
                [self.hdc_path, "tconn", address],
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            output = result.stdout + result.stderr

            if "Connect OK" in output or "connected" in output.lower():
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
            if address:
                cmd = [self.hdc_path, "tdisconn", address]
            else:
                # HDC 没有“断开全部”命令，需要先列出再逐个断开
                devices = self.list_devices()
                for device in devices:
                    if ":" in device.device_id:  # 远程设备
                        _run_hdc_command(
                            [self.hdc_path, "tdisconn", device.device_id],
                            capture_output=True,
                            text=True,
                            timeout=5
                        )
                return True, "Disconnected all remote devices"

            result = _run_hdc_command(cmd, capture_output=True, text=True, encoding="utf-8", timeout=5)

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
        # 关键步骤：列出当前可用的 HDC 设备
        try:
            result = _run_hdc_command(
                [self.hdc_path, "list", "targets"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            devices = []
            for line in result.stdout.strip().split("\n"):
                if not line.strip():
                    continue

                # HDC 输出格式: device_id (status)
                # 示例: "192.168.1.100:5555" 或 "FMR0223C13000649"
                device_id = line.strip()

                # 判断连接类型
                if ":" in device_id:
                    conn_type = ConnectionType.REMOTE
                else:
                    conn_type = ConnectionType.USB

                # HDC 的列表命令不提供详细状态
                # 对出现的设备默认视为已连接
                devices.append(
                    DeviceInfo(
                        device_id=device_id,
                        status="device",
                        connection_type=conn_type,
                        model=None,
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
            return len(devices) > 0

        return any(d.device_id == device_id for d in devices)

    def enable_tcpip(
        self, port: int = 5555, device_id: str | None = None
    ) -> tuple[bool, str]:
        """
        在 USB 连接的设备上启用 TCP/IP 调试。

        这将允许后续通过无线连接设备。

        参数:
            port: HDC 的 TCP 端口（默认: 5555）。
            device_id: 设备 ID。为 None 时使用第一个可用设备。

        返回:
            (success, message) 的元组。

        说明:
            设备必须先通过 USB 连接。
            启用后可拔掉 USB，通过 WiFi 连接。
        """
        # 关键步骤：开启设备 TCP/IP 调试模式
        try:
            cmd = [self.hdc_path]
            if device_id:
                cmd.extend(["-t", device_id])
            cmd.extend(["tmode", "port", str(port)])

            result = _run_hdc_command(cmd, capture_output=True, text=True, encoding="utf-8", timeout=10)

            output = result.stdout + result.stderr

            if result.returncode == 0 or "success" in output.lower():
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
            cmd = [self.hdc_path]
            if device_id:
                cmd.extend(["-t", device_id])
            cmd.extend(["shell", "ifconfig"])

            result = _run_hdc_command(cmd, capture_output=True, text=True, encoding="utf-8", timeout=5)

            # 从 ifconfig 输出中解析 IP
            for line in result.stdout.split("\n"):
                if "inet addr:" in line or "inet " in line:
                    parts = line.strip().split()
                    for i, part in enumerate(parts):
                        if "addr:" in part:
                            ip = part.split(":")[1]
                            # 过滤本地地址
                            if not ip.startswith("127."):
                                return ip
                        elif part == "inet" and i + 1 < len(parts):
                            ip = parts[i + 1].split("/")[0]
                            if not ip.startswith("127."):
                                return ip

            return None

        except Exception as e:
            print(f"Error getting device IP: {e}")
            return None

    def restart_server(self) -> tuple[bool, str]:
        """
        重启 HDC 服务。

        返回:
            (success, message) 的元组。
        """
        # 关键步骤：重启 HDC 服务端
        try:
            # 终止服务
            _run_hdc_command(
                [self.hdc_path, "kill"], capture_output=True, timeout=5
            )

            time.sleep(TIMING_CONFIG.connection.server_restart_delay)

            # 启动服务（HDC 在执行命令时会自动启动）
            _run_hdc_command(
                [self.hdc_path, "start", "-r"], capture_output=True, timeout=5
            )

            return True, "HDC server restarted"

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
    conn = HDCConnection()
    return conn.connect(address)


def list_devices() -> list[DeviceInfo]:
    """
    快速列出已连接设备的辅助方法。

    返回:
        DeviceInfo 对象列表。
    """
    # 关键步骤：列出当前可用的 HDC 设备
    conn = HDCConnection()
    return conn.list_devices()

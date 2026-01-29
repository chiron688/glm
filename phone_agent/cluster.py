"""Multi-device cluster runner for COTA agents."""

from __future__ import annotations

from dataclasses import dataclass, replace
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable

from phone_agent.device_factory import DeviceType
from phone_agent.model import ModelConfig
from phone_agent.cota import COTAConfig, COTAPhoneAgent, COTAIOSAgent, COTAIOSAgentConfig
from phone_agent.agent import AgentConfig


@dataclass(frozen=True)
class DeviceEndpoint:
    device_type: DeviceType
    device_id: str | None
    wda_url: str | None = None


class ClusterRunner:
    def __init__(
        self,
        endpoints: list[DeviceEndpoint],
        model_config: ModelConfig,
        cota_config: COTAConfig,
        agent_config: AgentConfig | None = None,
        ios_agent_config: COTAIOSAgentConfig | None = None,
        parallel: bool = True,
        confirmation_callback: Callable[[str], bool] | None = None,
        takeover_callback: Callable[[str], None] | None = None,
    ) -> None:
        """执行 __init__ 相关逻辑。"""
        # 处理 __init__ 的主要逻辑
        self.endpoints = endpoints
        self.model_config = model_config
        self.cota_config = cota_config
        self.agent_config = agent_config or AgentConfig()
        self.ios_agent_config = ios_agent_config or COTAIOSAgentConfig()
        self.parallel = parallel
        self.confirmation_callback = confirmation_callback
        self.takeover_callback = takeover_callback

    def run(self, task: str) -> dict[str, str]:
        """执行 run 相关逻辑。"""
        # 处理 run 的主要逻辑
        if self.parallel and len(self.endpoints) > 1:
            return self._run_parallel(task)
        return self._run_sequential(task)

    def _run_parallel(self, task: str) -> dict[str, str]:
        """执行 _run_parallel 相关逻辑。"""
        # 处理 _run_parallel 的主要逻辑
        results: dict[str, str] = {}
        with ThreadPoolExecutor(max_workers=len(self.endpoints)) as executor:
            future_map = {
                executor.submit(self._run_on_endpoint, endpoint, task): endpoint
                for endpoint in self.endpoints
            }
            for future in as_completed(future_map):
                endpoint = future_map[future]
                key = endpoint.device_id or endpoint.wda_url or "unknown"
                try:
                    results[key] = future.result()
                except Exception as exc:
                    results[key] = f"error: {exc}"
        return results

    def _run_sequential(self, task: str) -> dict[str, str]:
        """执行 _run_sequential 相关逻辑。"""
        # 处理 _run_sequential 的主要逻辑
        results: dict[str, str] = {}
        for endpoint in self.endpoints:
            key = endpoint.device_id or endpoint.wda_url or "unknown"
            try:
                results[key] = self._run_on_endpoint(endpoint, task)
            except Exception as exc:
                results[key] = f"error: {exc}"
        return results

    def _run_on_endpoint(self, endpoint: DeviceEndpoint, task: str) -> str:
        """执行 _run_on_endpoint 相关逻辑。"""
        # 处理 _run_on_endpoint 的主要逻辑
        if endpoint.device_type == DeviceType.IOS:
            agent_config = replace(
                self.ios_agent_config,
                wda_url=endpoint.wda_url or self.ios_agent_config.wda_url,
                device_id=endpoint.device_id,
            )
            agent = COTAIOSAgent(
                model_config=self.model_config,
                agent_config=agent_config,
                cota_config=self.cota_config,
                confirmation_callback=self.confirmation_callback,
                takeover_callback=self.takeover_callback,
            )
            return agent.run(task)

        agent_config = replace(self.agent_config, device_id=endpoint.device_id)
        agent = COTAPhoneAgent(
            model_config=self.model_config,
            agent_config=agent_config,
            cota_config=self.cota_config,
            confirmation_callback=self.confirmation_callback,
            takeover_callback=self.takeover_callback,
        )
        return agent.run(task)

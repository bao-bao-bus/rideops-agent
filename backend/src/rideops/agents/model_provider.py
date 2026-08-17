import json
from dataclasses import dataclass
from urllib.request import Request, urlopen

from rideops.config import Settings


@dataclass(frozen=True)
class AgentModelStatus:
    provider: str
    model: str | None
    configured: bool
    enabled: bool
    purpose: str


class AgentModelProvider:
    """Optional model boundary. It may assist language tasks but never executes business writes."""

    def status(self) -> AgentModelStatus:
        raise NotImplementedError

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        raise NotImplementedError


class DisabledAgentModelProvider(AgentModelProvider):
    def __init__(self, reason: str = "模型 API 尚未启用") -> None:
        self.reason = reason

    def status(self) -> AgentModelStatus:
        return AgentModelStatus(
            provider="disabled",
            model=None,
            configured=False,
            enabled=False,
            purpose="预留给意图识别、字段抽取、查询改写和回复润色；不得直接写入业务数据。",
        )

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        raise RuntimeError(self.reason)


class OpenAICompatibleAgentModelProvider(AgentModelProvider):
    def __init__(self, base_url: str, api_key: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    def status(self) -> AgentModelStatus:
        return AgentModelStatus(
            provider="openai_compatible",
            model=self.model,
            configured=True,
            enabled=False,
            purpose="适配器已就绪但默认不参与客服决策；启用时只处理语言任务，业务写入仍由流程和工具边界控制。",
        )

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        payload = json.dumps(
            {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.2,
            }
        ).encode("utf-8")
        request = Request(
            self.base_url + "/chat/completions",
            data=payload,
            headers={"Authorization": "Bearer " + self.api_key, "Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8"))
        return body["choices"][0]["message"]["content"]


def build_agent_model_provider(settings: Settings) -> AgentModelProvider:
    if settings.agent_model_provider == "openai_compatible" and settings.agent_model_base_url and settings.agent_model_api_key and settings.agent_model:
        return OpenAICompatibleAgentModelProvider(settings.agent_model_base_url, settings.agent_model_api_key, settings.agent_model)
    return DisabledAgentModelProvider()

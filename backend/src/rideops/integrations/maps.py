import asyncio
import json
from collections.abc import Mapping
from typing import Any, Protocol
from urllib.parse import urlencode

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


class MapProvider(Protocol):
    def estimate_trip(self, origin: str, destination: str) -> dict[str, Any]:
        """Return a normalized route estimate for the pre-trip customer flow."""


class SyntheticMapProvider:
    def estimate_trip(self, origin: str, destination: str) -> dict[str, Any]:
        return {
            "distance_km": 4.2,
            "estimated_minutes": 18,
            "estimated_fee": 8.5,
            "currency": "CNY",
            "source": "synthetic_estimator",
            "pricing_source": "synthetic_pricing",
        }


class MapProviderError(RuntimeError):
    pass


class AmapMcpProvider:
    """MCP client adapter for the official Amap remote server.

    The adapter normalizes Amap's tool response so the rest of RideOps does not
    depend on a third-party MCP tool schema. Pricing remains RideOps-owned.
    """

    def __init__(self, api_key: str, timeout_seconds: float = 20.0) -> None:
        if not api_key:
            raise ValueError("AMAP_API_KEY is required for the Amap MCP provider")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def estimate_trip(self, origin: str, destination: str) -> dict[str, Any]:
        try:
            return asyncio.run(self._estimate_trip(origin, destination))
        except Exception as exc:  # pragma: no cover - remote failures vary by provider
            raise MapProviderError(f"Amap MCP route lookup failed: {exc}") from exc

    async def _estimate_trip(self, origin: str, destination: str) -> dict[str, Any]:
        endpoint = "https://mcp.amap.com/mcp?" + urlencode({"key": self.api_key})
        async with streamable_http_client(endpoint) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await asyncio.wait_for(session.initialize(), timeout=self.timeout_seconds)
                tools = await asyncio.wait_for(session.list_tools(), timeout=self.timeout_seconds)
                geo_tool = self._select_tool(tools.tools, "maps_geo")
                route_tool = self._select_tool(tools.tools, "maps_direction_bicycling")
                origin_result = await self._call_tool(session, geo_tool.name, {"address": origin})
                destination_result = await self._call_tool(session, geo_tool.name, {"address": destination})
                origin_location = self._extract_location(self._result_payload(origin_result))
                destination_location = self._extract_location(self._result_payload(destination_result))
                if not origin_location or not destination_location:
                    raise MapProviderError("Amap MCP geocoding returned no location")
                result = await self._call_tool(
                    session,
                    route_tool.name,
                    {"origin": origin_location, "destination": destination_location},
                )
        payload = self._result_payload(result)
        distance_m = self._find_number(payload, {"distance"})
        duration_s = self._find_number(payload, {"duration"})
        if distance_m is None or duration_s is None:
            raise MapProviderError("Amap MCP returned no route distance or duration")
        minutes = max(1, round(duration_s / 60))
        distance_km = round(distance_m / 1000, 2)
        estimated_fee = round(1.5 + minutes * 0.5, 2)
        return {
            "distance_km": distance_km,
            "estimated_minutes": minutes,
            "estimated_fee": estimated_fee,
            "currency": "CNY",
            "source": "amap_mcp",
            "pricing_source": "rideops_synthetic_pricing",
            "assumptions": ["路线由高德 MCP 提供", "费用为 RideOps 合成计价预估，最终以实际订单为准"],
        }

    @staticmethod
    def _select_tool(tools: list[Any], suffix: str) -> Any:
        candidates = [tool for tool in tools if suffix.lower() in tool.name.lower()]
        if not candidates:
            raise MapProviderError(f"Amap MCP does not expose a tool matching {suffix}")
        return candidates[0]

    async def _call_tool(self, session: ClientSession, name: str, arguments: dict[str, str]) -> Any:
        return await asyncio.wait_for(session.call_tool(name, arguments), timeout=self.timeout_seconds)

    @classmethod
    def _result_payload(cls, result: Any) -> Any:
        if getattr(result, "isError", False):
            message = " ".join(getattr(item, "text", "") for item in getattr(result, "content", []) or [])
            raise MapProviderError(message or "Amap MCP tool returned an error")
        structured = getattr(result, "structuredContent", None)
        if structured:
            return structured
        texts: list[str] = []
        for item in getattr(result, "content", []) or []:
            text = getattr(item, "text", None)
            if text:
                texts.append(text)
        raw = "\n".join(texts).strip()
        if not raw:
            raise MapProviderError("Amap MCP returned an empty response")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"text": raw}

    @classmethod
    def _extract_location(cls, value: Any) -> str | None:
        if isinstance(value, Mapping):
            for key, item in value.items():
                if key.lower() == "location" and isinstance(item, str):
                    return item
                found = cls._extract_location(item)
                if found:
                    return found
        elif isinstance(value, list):
            for item in value:
                found = cls._extract_location(item)
                if found:
                    return found
        return None

    @classmethod
    def _find_number(cls, value: Any, keys: set[str]) -> float | None:
        if isinstance(value, Mapping):
            for key, item in value.items():
                if key.lower() in keys and isinstance(item, (int, float)):
                    return float(item)
                found = cls._find_number(item, keys)
                if found is not None:
                    return found
        elif isinstance(value, list):
            for item in value:
                found = cls._find_number(item, keys)
                if found is not None:
                    return found
        return None


def build_map_provider(provider_name: str, api_key: str) -> MapProvider:
    if provider_name.lower() in {"amap", "amap_mcp"} and api_key:
        return AmapMcpProvider(api_key)
    return SyntheticMapProvider()

from pydantic import BaseModel, ConfigDict, Field

from .registry import SkillRegistry, SkillSummary


class SkillRouteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(min_length=1)


class SkillRouteResult(BaseModel):
    skill: SkillSummary | None
    matched_terms: list[str]
    loaded: bool = False


class SkillRouter:
    RULES = {
        "accident-handling": ("事故", "故障", "损坏", "碰撞", "受伤", "车辆问题"),
        "long-rental-planning": ("长租", "租期", "月租", "长期租赁", "续租", "租车计划"),
    }

    def __init__(self, registry: SkillRegistry) -> None:
        self.registry = registry

    def route(self, message: str) -> SkillRouteResult:
        candidates = [(name, [term for term in terms if term in message]) for name, terms in self.RULES.items()]
        name, terms = max(candidates, key=lambda item: len(item[1]), default=(None, []))
        skill = self.registry.get(name) if name and terms else None
        return SkillRouteResult(skill=skill, matched_terms=terms)

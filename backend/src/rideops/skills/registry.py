import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class SkillSummary(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str
    description: str


class LoadedSkill(SkillSummary):
    content: str
    references: list[str]
    templates: list[str]


class SkillRegistry:
    """Indexes only metadata at startup; full skill files are loaded on demand."""

    def __init__(self, skills_dir: Path) -> None:
        self.skills_dir = Path(skills_dir)
        self._summaries: dict[str, SkillSummary] = {}
        self.refresh()

    def refresh(self) -> None:
        self._summaries = {}
        for skill_file in sorted(self.skills_dir.glob("*/SKILL.md")):
            metadata = self._read_metadata(skill_file)
            if metadata:
                self._summaries[metadata.name] = metadata

    @staticmethod
    def _read_metadata(path: Path) -> SkillSummary | None:
        text = path.read_text(encoding="utf-8")
        name_match = re.search(r"^name:\s*(.+)$", text, re.MULTILINE)
        description_match = re.search(r"^description:\s*(.+)$", text, re.MULTILINE)
        if not name_match or not description_match:
            return None
        return SkillSummary(name=name_match.group(1).strip(), description=description_match.group(1).strip())

    def list(self) -> list[SkillSummary]:
        return list(self._summaries.values())

    def get(self, name: str) -> SkillSummary | None:
        return self._summaries.get(name)

    def load(self, name: str) -> LoadedSkill:
        summary = self._summaries.get(name)
        if summary is None:
            raise KeyError(name)
        directory = self.skills_dir / name
        return LoadedSkill(
            **summary.model_dump(),
            content=(directory / "SKILL.md").read_text(encoding="utf-8"),
            references=sorted(p.name for p in (directory / "references").glob("*") if p.is_file()),
            templates=sorted(p.name for p in (directory / "templates").glob("*") if p.is_file()),
        )

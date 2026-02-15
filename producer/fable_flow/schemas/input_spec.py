"""Input specification schema for FableFlow book-first architecture."""

from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class CharacterRole(StrEnum):
    PROTAGONIST = "protagonist"
    SUPPORTING = "supporting"
    ANTAGONIST = "antagonist"
    MINOR = "minor"


class Appearance(BaseModel):
    """Physical appearance description for a character."""

    heritage: str = Field(..., description="Cultural/ethnic heritage (e.g., 'Indian Australian')")
    skin_tone: str
    hair: str
    eyes: str
    distinctive_features: list[str] = Field(default_factory=list)


class Character(BaseModel):
    name: str = Field(..., min_length=1)
    age: int | None = Field(None, ge=1, le=100)
    role: CharacterRole
    personality: str
    appearance: Appearance
    typical_clothing: str
    relationship: str | None = None


class Setting(BaseModel):
    """Rich setting description. A plain string is auto-promoted to `primary`."""

    primary: str = Field(..., description="The main location/context")
    secondary: str | None = Field(
        None, description="Other notable locations (e.g., 'train ride and home at bedtime')"
    )
    locations_visited: list[str] = Field(
        default_factory=list,
        description="Detailed list of waypoints / exhibits / scenes within the primary setting",
    )


class VocabularyWord(BaseModel):
    """A new word the story should introduce, with a child-friendly meaning."""

    word: str
    kid_friendly_meaning: str


class ChapterOutlineItem(BaseModel):
    """One planned chapter. When present in `chapter_outline`, agents follow this structure."""

    number: int = Field(..., ge=1)
    title: str
    beats: str = Field(..., description="What happens in this chapter, told in a sentence or two")
    introduces: str | None = Field(
        None, description="A new concept, character, or motif this chapter introduces"
    )


class FeaturedMoment(BaseModel):
    """A specific scene the story must build toward and render carefully."""

    where: str = Field(..., description="Where in the story this moment lives (e.g., 'Chapter 6')")
    purpose: str = Field(..., description="Why this scene matters")
    core_message: str | None = None
    draft_text: str | None = Field(
        None,
        description="Optional pre-written text for this scene; the LLM should fold it in faithfully",
    )


class BackMatterPlan(BaseModel):
    """Author's plan for the back matter, used as guidance for the enrichment agents."""

    for_kids: str | None = Field(
        None, description="Guidance for the experiment / 'For Amazing Young Scientists' page"
    )
    for_parents: str | None = Field(
        None,
        description="Note for parents and educators — rendered as its own back-matter page if set",
    )
    extended_biography: str | None = Field(
        None, description="Extra biographical context for the dedicated personality"
    )


class StorySeed(BaseModel):
    """Seed information for story generation."""

    theme: str = Field(..., description="Main theme or subject")
    setting: Setting = Field(..., description="Primary setting (string is auto-promoted)")
    premise: str | None = Field(
        None,
        description="One-line story premise / pitch (e.g., 'When Cassie's phone surprises her...')",
    )
    tone_and_voice: str | None = Field(
        None,
        description="Voice guidance for the writer ('warm, curious, playful; short sentences')",
    )
    recurring_motifs: list[str] = Field(
        default_factory=list,
        description="Repeating threads/imagery the story should weave (e.g., 'tiny coloured dots')",
    )
    vocabulary_introduced: list[VocabularyWord] = Field(
        default_factory=list,
        description="Words to teach the reader, with kid-friendly meanings",
    )
    story_arc: dict[str, str] = Field(
        default_factory=dict,
        description="Free-form act-by-act structure (e.g., {'act_1_wonder': '...'})",
    )
    chapter_outline: list[ChapterOutlineItem] = Field(
        default_factory=list,
        description="Optional chapter-by-chapter plan; if set, the chapter agent uses it verbatim",
    )
    featured_moment: FeaturedMoment | None = Field(
        None, description="A specific scene to build the story around"
    )
    learning_objectives: list[str] = Field(default_factory=list)
    dedication_text: str | None = Field(
        None, description="Exact dedication text rendered on the dedication page"
    )
    back_matter: BackMatterPlan | None = Field(
        None, description="Author's plan for back-matter content"
    )
    draft_story: str | None = Field(
        None,
        description="Optional draft story; if provided, the writer uses it as the basis",
    )

    @field_validator("theme")
    @classmethod
    def validate_theme(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("theme cannot be empty or whitespace")
        return v

    @field_validator("setting", mode="before")
    @classmethod
    def coerce_setting(cls, v: Any) -> Any:
        """A plain string `setting` is promoted to Setting{primary=str}."""
        if isinstance(v, str):
            if not v.strip():
                raise ValueError("setting cannot be empty")
            return {"primary": v}
        return v


class ProjectMetadata(BaseModel):
    title: str = Field(..., min_length=1)
    subtitle: str | None = Field(None, description="Optional book subtitle (renders on cover)")
    series: str | None = None
    volume: int | None = Field(None, ge=1)
    target_age: int = Field(..., ge=3, le=12, description="Primary target age (3-12)")
    age_range: str | None = Field(
        None, description="Marketing age range (e.g., '5-10'); for display only"
    )
    genre: str
    tagline: str | None = Field(None, description="Short marketing tagline (renders on cover)")


class BookProductionConfig(BaseModel):
    format: list[Literal["pdf", "epub"]] = Field(default=["pdf", "epub"])
    page_count_target: int = Field(default=24, ge=8, le=100)
    illustration_style: str = Field(default="digital watercolor blend")
    illustration_motifs: list[str] = Field(
        default_factory=list,
        description="Recurring visual motifs the illustrator should weave across images",
    )

    @field_validator("format")
    @classmethod
    def validate_format_not_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("At least one output format must be specified")
        return v


class MovieProductionConfig(BaseModel):
    enabled: bool = Field(default=True)
    include_narration: bool = Field(default=True)
    include_subtitles: bool = Field(default=True)
    music_style: str = Field(default="gentle orchestral")


class ProductionConfig(BaseModel):
    book: BookProductionConfig = Field(default_factory=BookProductionConfig)
    movie: MovieProductionConfig = Field(default_factory=MovieProductionConfig)


class DedicatedPersonality(BaseModel):
    name: str = Field(..., min_length=1)
    field: str | None = None
    notable_for: str | None = Field(
        None, description="Hint for the biography agent: their key works/contributions"
    )
    why_this_dedication: str | None = Field(
        None, description="Why this book is dedicated to them; used in biography prompt"
    )


class FableFlowInput(BaseModel):
    """Complete input specification for FableFlow book-first architecture."""

    project: ProjectMetadata
    characters: list[Character] = Field(..., min_length=1)
    story_seed: StorySeed
    production_config: ProductionConfig = Field(default_factory=ProductionConfig)
    dedicated_to: DedicatedPersonality | None = None

    @field_validator("characters")
    @classmethod
    def validate_has_protagonist(cls, v: list[Character]) -> list[Character]:
        if not any(c.role == CharacterRole.PROTAGONIST for c in v):
            raise ValueError("At least one protagonist character is required")
        return v

    @classmethod
    def from_json_file(cls, path: str | Path) -> FableFlowInput:
        with open(path, encoding="utf-8") as f:
            return cls.model_validate(json.load(f))

    def to_json_file(self, path: str | Path, indent: int = 2) -> None:
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.model_dump_json(indent=indent))

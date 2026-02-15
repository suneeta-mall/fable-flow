"""Schema for the book artifact produced by Phase 1."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class IllustrationSpec(BaseModel):
    """A planned illustration in a chapter."""

    page: int = Field(..., ge=1, description="Page number where illustration appears")
    placement: Literal["full_page", "inline", "header", "footer"] = Field(...)
    description: str = Field(
        ...,
        description=(
            "Visual description used as the image-generation prompt. "
            "Internal-only; not shown to the reader."
        ),
    )
    caption: str | None = Field(
        None,
        description=(
            "Short reader-facing caption written in the story's voice. "
            "Rendered under the image in PDF/EPUB. May be None for an uncaptioned image."
        ),
    )
    characters: list[str] = Field(default_factory=list)
    scene_context: str = Field(..., description="e.g., 'morning, bedroom, excited'")
    image_path: str | None = Field(
        None, description="Path to the generated illustration file (set in Phase 1)"
    )


class ReflectionSection(BaseModel):
    """Three reflection questions at the end of a chapter."""

    questions: list[str] = Field(..., min_length=3, max_length=3)


class Chapter(BaseModel):
    number: int = Field(..., ge=1)
    title: str = Field(...)
    text: str = Field(..., description="Chapter prose, with the poem extracted out")
    poem: str | None = Field(
        None,
        description=(
            "A short thematic poem (haiku, quatrain, free verse, ...) that distils "
            "the chapter's emotional or educational core. Renders set off from prose "
            "in PDF/EPUB. Newlines preserved."
        ),
    )
    page_start: int = Field(..., ge=1)
    page_end: int = Field(..., ge=1)
    illustrations: list[IllustrationSpec] = Field(default_factory=list)
    reflection: ReflectionSection | None = Field(
        None, description="3 reflection questions, set by the enrichment phase"
    )


class Experiment(BaseModel):
    """A hands-on activity that lets the child experience the book's concept."""

    title: str
    concept: str = Field(..., description="The idea the experiment demonstrates")
    materials: list[str] = Field(..., min_length=1)
    steps: list[str] = Field(..., min_length=2)
    what_to_observe: str
    safety_note: str | None = None


class Biography(BaseModel):
    """One-pager about the personality the book is dedicated to."""

    name: str
    title: str = Field(..., description="e.g., 'Physicist & Author'")
    lifespan: str | None = Field(None, description="e.g., '1942 – 2018'")
    one_line: str = Field(..., description="Single-sentence tagline")
    summary: str = Field(..., description="2-3 paragraph summary written for children")
    fun_facts: list[str] = Field(..., min_length=3, max_length=12)
    why_inspiring: str = Field(
        ..., description="A short paragraph on why this person inspires kids"
    )


class BookMetadata(BaseModel):
    title: str = Field(...)
    subtitle: str | None = Field(None, description="Renders on the cover")
    tagline: str | None = Field(None, description="Short marketing tagline; renders on the cover")
    series: str | None = None
    volume: int | None = None
    target_age: int = Field(...)
    page_count: int = Field(...)
    author: str = Field(default="FableFlow AI")
    genre: str = Field(...)
    dedication_text: str | None = Field(
        None, description="Rendered on its own dedication page in the front matter"
    )
    premise: str | None = Field(
        None,
        description="One-line story pitch — used on the back cover when available",
    )


class CoverImages(BaseModel):
    """Front and back cover images after illustration + text overlay.

    `front_path` / `back_path` point at the final composited PNGs (illustration
    with title/author/tagline text rendered over it). `*_base_path` are the raw
    text-free illustrations kept around for re-overlay without re-generation.
    """

    front_path: str = Field(..., description="Composited front cover (with text overlay)")
    back_path: str = Field(..., description="Composited back cover (with text overlay)")
    front_base_path: str | None = Field(
        None, description="Raw text-free front illustration, before overlay"
    )
    back_base_path: str | None = Field(
        None, description="Raw text-free back illustration, before overlay"
    )


class CharacterReference(BaseModel):
    """Canonical reference images for a character, used to anchor visual consistency.

    Populated by `CharacterReferenceAgent` before any chapter illustrations are
    generated. Downstream illustration generation feeds `portrait_path` (and,
    where helpful, `full_body_path`) into the image model as visual conditioning
    via IP-Adapter, so the same character looks the same in every scene.
    """

    name: str = Field(..., description="Must match a character name in input_spec.characters")
    portrait_path: str | None = Field(
        None, description="Head-and-shoulders reference (used for IP-Adapter conditioning)"
    )
    full_body_path: str | None = Field(
        None, description="Full-body reference (used for action shots when helpful)"
    )


class BookContent(BaseModel):
    """Complete book content output from Phase 1."""

    metadata: BookMetadata = Field(...)
    chapters: list[Chapter] = Field(..., min_length=1)
    full_text: str = Field(...)
    characters_used: list[str] = Field(...)
    character_references: list[CharacterReference] = Field(
        default_factory=list,
        description="Canonical visual references per character (set during Phase 1)",
    )
    experiment: Experiment | None = Field(
        None, description="Hands-on activity, set by the enrichment phase"
    )
    biography: Biography | None = Field(
        None, description="Featured personality biography, set when dedicated_to is provided"
    )
    back_matter_for_parents: str | None = Field(
        None,
        description="Optional 'For Parents & Educators' page rendered after experiment/biography",
    )
    cover: CoverImages | None = Field(
        None, description="Front and back cover images (set by CoverDesignerAgent)"
    )

    @classmethod
    def from_json_file(cls, path: str | Path) -> BookContent:
        with open(path, encoding="utf-8") as f:
            return cls.model_validate(json.load(f))

    def to_json_file(self, path: str | Path, indent: int = 2) -> None:
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.model_dump_json(indent=indent))

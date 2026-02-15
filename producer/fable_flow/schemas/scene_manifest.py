from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class NarrationAsset(BaseModel):
    file: str = Field(..., description="Path to narration audio file")
    duration: float = Field(..., gt=0, description="Actual duration in seconds")
    text_chunks: list[str] = Field(
        default_factory=list, description="Text chunks for subtitle timing"
    )


class ImageAsset(BaseModel):
    file: str = Field(..., description="Path to image file")
    source: Literal["book", "generated"] = Field(..., description="Origin of image")
    width: int | None = None
    height: int | None = None


class VideoAsset(BaseModel):
    file: str = Field(..., description="Path to video file")
    duration: float = Field(..., gt=0, description="Video duration in seconds")
    fps: float = Field(default=25.0, description="Frames per second")


class MusicAsset(BaseModel):
    file: str = Field(..., description="Path to music file")
    duration: float = Field(..., gt=0, description="Music duration in seconds")
    fade_in: float = Field(default=0.5)
    fade_out: float = Field(default=0.5)


class SubtitleAsset(BaseModel):
    file: str = Field(..., description="Path to subtitle file (SRT)")
    format: Literal["SRT", "VTT"] = Field(default="SRT")


class SceneSpec(BaseModel):
    """Specification for a single scene in the movie."""

    id: str = Field(..., description="Unique scene ID (e.g., 'ch1_scene01')")
    chapter: int = Field(..., ge=1)
    sequence: int = Field(..., ge=1)
    text: str = Field(..., description="Narrative text for this scene")
    page_reference: int | None = None
    characters: list[str] = Field(default_factory=list)
    setting: str = Field(...)
    mood: str = Field(...)
    illustration_reference: str | None = Field(
        None, description="Path to book illustration to reuse, if applicable"
    )
    estimated_duration: float = Field(..., gt=0)

    narration: NarrationAsset | None = None
    image: ImageAsset | None = None
    video: VideoAsset | None = None
    music: MusicAsset | None = None
    subtitles: SubtitleAsset | None = None
    composite: str | None = None


class SceneManifest(BaseModel):
    """Complete scene manifest for movie production."""

    book_title: str = Field(...)
    total_scenes: int = Field(..., ge=1)
    estimated_total_duration: float = Field(..., gt=0)
    scenes: list[SceneSpec] = Field(..., min_length=1)

    @classmethod
    def from_json_file(cls, path: str | Path) -> SceneManifest:
        with open(path, encoding="utf-8") as f:
            return cls.model_validate(json.load(f))

    def to_json_file(self, path: str | Path, indent: int = 2) -> None:
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.model_dump_json(indent=indent))

from pathlib import Path

import aiofiles
from moviepy import ImageSequenceClip
from pydantic import BaseModel, ConfigDict

BASE_DIR = Path(__file__).resolve().parent

BASE_DATA_DIR = BASE_DIR / "data"


class Manuscript(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    story: str
    synopsis: str
    images: list[str] = []
    clips: list[ImageSequenceClip] | None = None


async def read_story(story_fn: Path) -> str:
    async with aiofiles.open(story_fn, encoding="utf-8") as f:
        content = await f.read()
        return str(content)


async def read_synopsis(story_fn: Path) -> str:
    async with aiofiles.open(story_fn, encoding="utf-8") as f:
        content = await f.read()
        return str(content)

import asyncio
from pathlib import Path

import typer
from autogen_core import (
    SingleThreadedAgentRuntime,
    TopicId,
)

from fable_flow.agents import (
    NarratorAgent,
)
from fable_flow.common import Manuscript, read_story, read_synopsis
from fable_flow.config import config

app = typer.Typer()


async def generate_narration_from_fn(
    story_fn: Path = Path(config.paths.output),
    destination: Path = Path(config.paths.output),
) -> None:
    destination.mkdir(parents=True, exist_ok=True)

    if story_fn.is_dir():
        story_fn = story_fn / "final_story.txt"

    story = await read_story(story_fn)
    synopsis = await read_synopsis(story_fn.parent / "draft_synopsis.txt")

    runtime = SingleThreadedAgentRuntime()

    await NarratorAgent.register(
        runtime,
        type=config.agent_types.narrator,
        factory=lambda: NarratorAgent(output_dir=destination),
    )

    runtime.start()

    await runtime.publish_message(
        Manuscript(story=story, synopsis=synopsis),
        TopicId(config.agent_types.narrator, source="narration_generator"),
    )

    await runtime.stop_when_idle()


@app.command()
def produce(
    ctx: typer.Context,
    story_fn: Path = Path(config.paths.output),
    destination: Path = Path(config.paths.output),
) -> None:
    asyncio.run(
        generate_narration_from_fn(
            story_fn=story_fn,
            destination=destination,
        )
    )


if __name__ == "__main__":
    app()

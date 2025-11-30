import asyncio
from pathlib import Path

import typer
from autogen_core import (
    SingleThreadedAgentRuntime,
    TopicId,
)

from fable_flow.agents import (
    MusicDirectorAgent,
    MusicianAgent,
)
from fable_flow.client import FableFlowChatClient
from fable_flow.common import Manuscript, read_story, read_synopsis
from fable_flow.config import config

app = typer.Typer()


async def generate_music_from_fn(
    story_fn: Path = Path(config.paths.output),
    destination: Path = Path(config.paths.output),
) -> None:
    destination.mkdir(parents=True, exist_ok=True)

    # Look for movie_director.txt (storyboard content) first
    storyboard_file = destination / "movie_director.txt"
    if storyboard_file.exists():
        # Use storyboard content for music generation
        story = await read_story(storyboard_file)
        synopsis_file = destination / "draft_synopsis.txt"
    else:
        # Fallback to story content if no storyboard exists
        if story_fn.is_dir():
            story_fn = story_fn / "final_story.txt"
        story = await read_story(story_fn)
        synopsis_file = story_fn.parent / "draft_synopsis.txt"

    synopsis = await read_synopsis(synopsis_file)

    model_client = FableFlowChatClient.create_chat_client()

    runtime = SingleThreadedAgentRuntime()

    await MusicDirectorAgent.register(
        runtime,
        type=config.agent_types.music_director,
        factory=lambda: MusicDirectorAgent(model_client=model_client, output_dir=destination),
    )

    await MusicianAgent.register(
        runtime,
        type=config.agent_types.musician,
        factory=lambda: MusicianAgent(output_dir=destination),
    )

    runtime.start()

    await runtime.publish_message(
        Manuscript(story=story, synopsis=synopsis),
        TopicId(config.agent_types.music_director, source="music_generator"),
    )

    await runtime.stop_when_idle()


@app.command()
def produce(
    ctx: typer.Context,
    story_fn: Path = Path(config.paths.output),
    destination: Path = Path(config.paths.output),
) -> None:
    asyncio.run(
        generate_music_from_fn(
            story_fn=story_fn,
            destination=destination,
        )
    )


if __name__ == "__main__":
    app()

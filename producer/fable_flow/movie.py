import asyncio
from pathlib import Path

import typer
from autogen_core import (
    SingleThreadedAgentRuntime,
    TopicId,
)

from fable_flow.agents import (
    AnimatorAgent,
    MovieDirectorAgent,
    MovieProducerAgent,
    MusicDirectorAgent,
    MusicianAgent,
)
from fable_flow.client import FableFlowChatClient
from fable_flow.common import Manuscript, read_story, read_synopsis
from fable_flow.config import config

app = typer.Typer()


async def generate_movie_from_fn(
    story_fn: Path = Path(config.paths.output),
    destination: Path = Path(config.paths.output),
) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    if story_fn.is_dir():
        story_fn = story_fn / "final_story.txt"

    story = await read_story(story_fn)
    synopsis = await read_synopsis(story_fn.parent / "draft_synopsis.txt")

    model_client = FableFlowChatClient.create_chat_client()

    runtime = SingleThreadedAgentRuntime()

    await MovieDirectorAgent.register(
        runtime,
        type=config.agent_types.movie_director_type,
        factory=lambda: MovieDirectorAgent(model_client=model_client, output_dir=destination),
    )

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

    await AnimatorAgent.register(
        runtime,
        type=config.agent_types.animator,
        factory=lambda: AnimatorAgent(output_dir=destination),
    )

    await MovieProducerAgent.register(
        runtime,
        type=config.agent_types.movie_producer,
        factory=lambda: MovieProducerAgent(output_dir=destination),
    )

    runtime.start()

    await runtime.publish_message(
        Manuscript(story=story, synopsis=synopsis),
        topic_id=TopicId(config.agent_types.movie_director_type, source="default"),
    )

    await runtime.stop_when_idle()


@app.command()
def produce(
    ctx: typer.Context,
    story_fn: Path = Path(config.paths.output),
    destination: Path = Path(config.paths.output),
) -> None:
    asyncio.run(
        generate_movie_from_fn(
            story_fn=story_fn,
            destination=destination,
        )
    )


if __name__ == "__main__":
    app()

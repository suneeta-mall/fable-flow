import asyncio
from pathlib import Path

import aiofiles
import typer
from autogen_core import (
    SingleThreadedAgentRuntime,
    TopicId,
)

from fable_flow.agents import (
    BookProducerAgent,
)
from fable_flow.client import FableFlowChatClient
from fable_flow.common import Manuscript
from fable_flow.config import config

app = typer.Typer()


async def main(story_fn: Path, output_dir: Path = Path(config.paths.output)) -> None:
    """Main entry point for story generation."""
    output_dir.mkdir(parents=True, exist_ok=True)

    async with aiofiles.open(story_fn / "image_planner_story.txt") as f:
        story = await f.read()

    async with aiofiles.open(story_fn / "draft_synopsis.txt") as f:
        synopsis = await f.read()

    model_client = FableFlowChatClient.create_chat_client()

    runtime = SingleThreadedAgentRuntime()

    await BookProducerAgent.register(
        runtime,
        type=config.agent_types.producer,
        factory=lambda: BookProducerAgent(model_client=model_client, output_dir=output_dir),
    )

    runtime.start()

    await runtime.publish_message(
        Manuscript(story=story, synopsis=synopsis),
        topic_id=TopicId(config.agent_types.producer, source="default"),
    )

    await runtime.stop_when_idle()


@app.command()
def process(
    ctx: typer.Context,
    story_fn: Path = Path(config.paths.output),
) -> None:
    asyncio.run(main(story_fn=story_fn))


if __name__ == "__main__":
    app()

import asyncio
from pathlib import Path

import aiofiles
import typer
from autogen_core import (
    SingleThreadedAgentRuntime,
    TopicId,
)

from fable_flow.agents import (
    IllustrationPlannerAgent,
    IllustratorAgent,
)
from fable_flow.client import FableFlowChatClient
from fable_flow.common import BASE_DATA_DIR, Manuscript
from fable_flow.config import config

app = typer.Typer()


async def main(
    story_fn: Path, synopsis_fn: Path, output_dir: Path = Path(config.paths.output)
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    if story_fn.is_dir():
        story_fn = story_fn / "draft_story.txt"
    if synopsis_fn.is_dir():
        synopsis_fn = synopsis_fn / "draft_synopsis.txt"

    async with aiofiles.open(story_fn) as f:
        story = await f.read()

    async with aiofiles.open(synopsis_fn) as f:
        synopsis = await f.read()

    model_client = FableFlowChatClient.create_chat_client()

    runtime = SingleThreadedAgentRuntime()

    await IllustrationPlannerAgent.register(
        runtime,
        type=config.agent_types.illustration_planner,
        factory=lambda: IllustrationPlannerAgent(model_client=model_client, output_dir=output_dir),
    )

    await IllustratorAgent.register(
        runtime,
        type=config.agent_types.illustrator,
        factory=lambda: IllustratorAgent(output_dir=output_dir),
    )

    runtime.start()

    await runtime.publish_message(
        Manuscript(story=story, synopsis=synopsis),
        TopicId(config.agent_types.illustration_planner, source="default"),
    )

    await runtime.stop_when_idle()


@app.command()
def draw(
    ctx: typer.Context,
    story_fn: Path = Path(config.paths.output),
    synopsis_fn: Path = Path(config.paths.output) / "draft_synopsis.txt",
) -> None:
    asyncio.run(main(story_fn=story_fn, synopsis_fn=synopsis_fn))


if __name__ == "__main__":
    app()

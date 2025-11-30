import asyncio
from pathlib import Path

import aiofiles
import openai
import typer
from autogen_core import (
    SingleThreadedAgentRuntime,
    TopicId,
)

from fable_flow.agents import (
    AnimatorAgent,
    BookProducerAgent,
    ContentModeratorAgent,
    CritiqueAgent,
    EditorAgent,
    FormatProofAgent,
    FriendProofReaderAgent,
    IllustrationPlannerAgent,
    IllustratorAgent,
    MovieDirectorAgent,
    MovieProducerAgent,
    MusicDirectorAgent,
    MusicianAgent,
    NarratorAgent,
    UserAgent,
)
from fable_flow.client import FableFlowChatClient
from fable_flow.common import Manuscript
from fable_flow.config import config

app = typer.Typer()


async def main(
    story_fn: Path = Path(config.paths.output),
    base_url: str = config.model.server.url,
    model_name: str = config.model.default,
    temperature: float = 0.9,
    seed: int = 42,
    output_dir: Path = Path(config.paths.output),
    simple_publish: bool = True,
):
    output_dir.mkdir(parents=True, exist_ok=True)

    async with aiofiles.open(story_fn / "draft_story.txt") as f:
        story = await f.read()

    async with aiofiles.open(story_fn / "draft_synopsis.txt") as f:
        synopsis = await f.read()

    model_client = FableFlowChatClient.create_chat_client(
        model=model_name, base_url=base_url, temperature=temperature, seed=seed
    )

    runtime = SingleThreadedAgentRuntime()

    agents = (
        []
        if simple_publish
        else [
            (FriendProofReaderAgent, config.agent_types.author_friend),
        ]
    )
    agents.extend(
        [
            (CritiqueAgent, config.agent_types.critique),
            (ContentModeratorAgent, config.agent_types.content_moderator),
            (EditorAgent, config.agent_types.editor),
            (FormatProofAgent, config.agent_types.format_proof),
            (UserAgent, config.agent_types.user),
            (NarratorAgent, config.agent_types.narrator),
            (IllustrationPlannerAgent, config.agent_types.illustration_planner),
            (IllustratorAgent, config.agent_types.illustrator),
            (BookProducerAgent, config.agent_types.producer),
            (MovieDirectorAgent, config.agent_types.movie_director_type),
            (MusicDirectorAgent, config.agent_types.music_director),
            (MusicianAgent, config.agent_types.musician),
            (AnimatorAgent, config.agent_types.animator),
            (MovieProducerAgent, config.agent_types.movie_producer),
        ]
    )
    for agent_cls, topic_type in agents:

        def _cls_instance(cls_type):
            kwargs = {"output_dir": output_dir}
            if (
                "model_client" in cls_type.__init__.__code__.co_varnames
                and cls_type != FriendProofReaderAgent
            ):
                kwargs["model_client"] = model_client
            if "image_client" in cls_type.__init__.__code__.co_varnames:
                kwargs["image_client"] = openai.AsyncClient(
                    api_key=config.model.server.api_key,
                    base_url=config.model.server.url,
                    timeout=config.model.server.timeout,
                    max_retries=config.model.server.max_retries,
                )
            return cls_type(**kwargs)

        await agent_cls.register(
            runtime, type=topic_type, factory=lambda cls=agent_cls: _cls_instance(cls)
        )

    runtime.start()

    await runtime.publish_message(
        Manuscript(story=story, synopsis=synopsis),
        topic_id=TopicId(
            config.agent_types.critique if simple_publish else config.agent_types.author_friend,
            source="default",
        ),
    )

    await runtime.stop_when_idle()


@app.command()
def process(
    ctx: typer.Context,
    story_fn: Path = Path(config.paths.output),
    base_url: str = config.model.server.url,
    model_name: str = config.model.default,
    temperature: float = 0.9,
    seed: int = 42,
) -> None:
    asyncio.run(
        main(
            story_fn=story_fn,
            base_url=base_url,
            model_name=model_name,
            temperature=temperature,
            seed=seed,
        )
    )


if __name__ == "__main__":
    app()

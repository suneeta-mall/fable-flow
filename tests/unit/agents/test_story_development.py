from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from fable_flow.agents.story_development import (
    DraftStoryAgent,
    FinalProofAgent,
    StoryEditorAgent,
    format_characters,
)
from fable_flow.schemas.input_spec import (
    Appearance,
    Character,
    CharacterRole,
    FableFlowInput,
    ProjectMetadata,
    StorySeed,
)


@pytest.fixture
def sample_input_spec():
    return FableFlowInput(
        project=ProjectMetadata(
            title="Test Story",
            series="Test Series",
            volume=1,
            target_age=6,
            genre="adventure",
        ),
        characters=[
            Character(
                name="Cassie",
                age=6,
                role=CharacterRole.PROTAGONIST,
                personality="curious, brave",
                appearance=Appearance(
                    heritage="Indian Australian",
                    skin_tone="warm honey-brown",
                    hair="wavy black",
                    eyes="brown",
                    distinctive_features=["bright smile"],
                ),
                typical_clothing="sundress",
            )
        ],
        story_seed=StorySeed(
            theme="learning about nature",
            setting="forest",
            learning_objectives=["trees make oxygen"],
        ),
    )


def test_format_characters_includes_appearance(sample_input_spec):
    out = format_characters(sample_input_spec.characters)
    assert "CASSIE" in out
    assert "Indian Australian" in out
    assert "wavy black" in out
    assert "bright smile" in out
    assert "sundress" in out


def test_format_characters_omits_age_when_unset():
    char = Character(
        name="Mystery",
        role=CharacterRole.MINOR,
        personality="mysterious",
        appearance=Appearance(heritage="Unknown", skin_tone="pale", hair="hooded", eyes="hidden"),
        typical_clothing="cloak",
    )
    out = format_characters([char])
    assert "Age:" not in out
    assert "MYSTERY" in out


@pytest.mark.asyncio
async def test_draft_writes_to_output_dir(sample_input_spec, tmp_path):
    agent = DraftStoryAgent(model="x", output_dir=tmp_path, word_count_target=100)
    with patch.object(agent._model, "generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = "Once upon a time. " * 20
        story = await agent.generate_story(sample_input_spec)
    assert story.startswith("Once upon a time")
    assert (tmp_path / "draft_story.txt").exists()
    # The system prompt should reference the target age and word count target.
    system_prompt = mock_gen.call_args.args[1]
    assert "100 words" in system_prompt
    assert "ages 6" in system_prompt


@pytest.mark.asyncio
async def test_draft_with_user_draft_passes_through(sample_input_spec, tmp_path):
    sample_input_spec.story_seed.draft_story = "Initial draft seed."
    agent = DraftStoryAgent(model="x", output_dir=tmp_path, word_count_target=200)
    with patch.object(agent._model, "generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = "expanded story"
        await agent.generate_story(sample_input_spec)
    user_prompt = mock_gen.call_args.args[0]
    assert "Initial draft seed." in user_prompt
    assert "DRAFT STORY PROVIDED" in user_prompt


@pytest.mark.asyncio
async def test_editor_writes_to_output_dir(sample_input_spec, tmp_path):
    agent = StoryEditorAgent(model="x", output_dir=tmp_path)
    with patch.object(agent._model, "generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = "edited story"
        result = await agent.edit_story("draft", sample_input_spec)
    assert result == "edited story"
    assert (tmp_path / "edited_story.txt").read_text() == "edited story"


@pytest.mark.asyncio
async def test_proof_writes_to_output_dir(sample_input_spec, tmp_path):
    agent = FinalProofAgent(model="x", output_dir=tmp_path)
    with patch.object(agent._model, "generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = "polished story"
        result = await agent.proof_story("edited", sample_input_spec)
    assert result == "polished story"
    assert (tmp_path / "final_story.txt").read_text() == "polished story"

"""Chapter-by-chapter drafting: one LLM call per chapter, with rolling synopsis."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from fable_flow.agents.story_development import DraftStoryAgent
from fable_flow.schemas.input_spec import (
    Appearance,
    ChapterOutlineItem,
    Character,
    CharacterRole,
    FableFlowInput,
    ProjectMetadata,
    Setting,
    StorySeed,
    VocabularyWord,
)


@pytest.fixture
def spec_with_outline():
    return FableFlowInput(
        project=ProjectMetadata(title="Cassie & Pixels", target_age=8, genre="adventure"),
        characters=[
            Character(
                name="Cassie",
                age=6,
                role=CharacterRole.PROTAGONIST,
                personality="curious",
                appearance=Appearance(heritage="X", skin_tone="warm", hair="black", eyes="brown"),
                typical_clothing="dress",
            ),
            Character(
                name="Mum",
                age=35,
                role=CharacterRole.SUPPORTING,
                personality="patient",
                appearance=Appearance(heritage="X", skin_tone="warm", hair="black", eyes="brown"),
                typical_clothing="cardigan",
            ),
        ],
        story_seed=StorySeed(
            theme="how computers learn to see",
            setting=Setting(primary="museum"),
            recurring_motifs=["tiny coloured dots", "labels"],
            vocabulary_introduced=[
                VocabularyWord(word="pixel", kid_friendly_meaning="tiny coloured dot"),
                VocabularyWord(word="label", kid_friendly_meaning="a name attached to a picture"),
            ],
            chapter_outline=[
                ChapterOutlineItem(number=1, title="The Phone That Knew", beats="Cassie asks how."),
                ChapterOutlineItem(number=2, title="Pixels on the Train", beats="Zooming in."),
                ChapterOutlineItem(number=3, title="The Wall", beats="ImageNet wall reveal."),
            ],
        ),
    )


@pytest.mark.asyncio
async def test_outline_triggers_per_chapter_calls(spec_with_outline, tmp_path):
    """3 outline chapters → 3 LLM calls (one per chapter)."""
    agent = DraftStoryAgent(model="x", output_dir=tmp_path, word_count_target=3000)
    with patch.object(agent._model, "generate", new_callable=AsyncMock) as mock_gen:
        # Each call returns a chunk of prose + a tiny poem.
        mock_gen.return_value = (
            "She watched the morning light come up. "
            "A small thing turned into a big question. "
            "\n\n* * *\n\nLittle dot,\nbig question,\nmorning light.\n\n* * *\n"
        )
        story = await agent.generate_story(spec_with_outline)

    assert mock_gen.await_count == 3
    # All three chapter headings are present
    assert "CHAPTER 1 — THE PHONE THAT KNEW" in story
    assert "CHAPTER 2 — PIXELS ON THE TRAIN" in story
    assert "CHAPTER 3 — THE WALL" in story


@pytest.mark.asyncio
async def test_rolling_synopsis_accumulates(spec_with_outline, tmp_path):
    """Chapter N's prompt should include synopses of chapters 1..N-1."""
    agent = DraftStoryAgent(model="x", output_dir=tmp_path, word_count_target=3000)
    with patch.object(agent._model, "generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = "prose\n\n* * *\n\nverse\n\n* * *\n"
        await agent.generate_story(spec_with_outline)

    # First call: no synopsis yet
    call_1_user = mock_gen.call_args_list[0].args[0]
    assert "Story so far" not in call_1_user

    # Second call: chapter 1's beats appear in the synopsis
    call_2_user = mock_gen.call_args_list[1].args[0]
    assert "Story so far" in call_2_user
    assert "The Phone That Knew" in call_2_user
    assert "Cassie asks how." in call_2_user

    # Third call: chapters 1 and 2 are both there
    call_3_user = mock_gen.call_args_list[2].args[0]
    assert "The Phone That Knew" in call_3_user
    assert "Pixels on the Train" in call_3_user


@pytest.mark.asyncio
async def test_motifs_rotate_across_chapters(spec_with_outline, tmp_path):
    """With 2 motifs and 3 chapters, motifs rotate: ch1→m0, ch2→m1, ch3→m0."""
    agent = DraftStoryAgent(model="x", output_dir=tmp_path, word_count_target=3000)
    with patch.object(agent._model, "generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = "prose\n\n* * *\n\nverse\n\n* * *\n"
        await agent.generate_story(spec_with_outline)

    motif_per_call = []
    for call in mock_gen.call_args_list:
        user = call.args[0]
        if "tiny coloured dots" in user:
            motif_per_call.append("dots")
        elif "labels" in user:
            motif_per_call.append("labels")
        else:
            motif_per_call.append("none")

    assert motif_per_call == ["dots", "labels", "dots"]


@pytest.mark.asyncio
async def test_vocab_distributes_across_early_chapters(spec_with_outline, tmp_path):
    """2 vocab words → first chapter gets word 1, second gets word 2, third gets none."""
    agent = DraftStoryAgent(model="x", output_dir=tmp_path, word_count_target=3000)
    with patch.object(agent._model, "generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = "prose\n\n* * *\n\nverse\n\n* * *\n"
        await agent.generate_story(spec_with_outline)

    call_1, call_2, call_3 = (c.args[0] for c in mock_gen.call_args_list)
    assert "pixel" in call_1
    assert "label" in call_2
    assert "pixel" not in call_3 and "label" not in call_3


@pytest.mark.asyncio
async def test_draft_chapter_blocks_are_picked_per_chapter(spec_with_outline, tmp_path):
    """When draft_story has CHAPTER markers, each per-chapter call gets that chapter's draft block."""
    spec_with_outline.story_seed.draft_story = (
        "CHAPTER ONE — THE PHONE THAT KNEW\n\nSaturday morning prose.\n\n"
        "CHAPTER TWO — PIXELS ON THE TRAIN\n\nTrain ride prose.\n\n"
        "CHAPTER THREE — THE WALL\n\nMuseum wall prose.\n"
    )
    agent = DraftStoryAgent(model="x", output_dir=tmp_path, word_count_target=3000)
    with patch.object(agent._model, "generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = "prose\n\n* * *\n\nverse\n\n* * *\n"
        await agent.generate_story(spec_with_outline)

    call_1, call_2, call_3 = (c.args[0] for c in mock_gen.call_args_list)
    assert "Saturday morning prose" in call_1
    assert "Train ride prose" in call_2
    assert "Museum wall prose" in call_3
    # Chapter 1's block should NOT leak into chapter 2's prompt
    assert "Saturday morning prose" not in call_2


@pytest.mark.asyncio
async def test_no_outline_falls_back_to_one_shot(spec_with_outline, tmp_path):
    """Without chapter_outline, one LLM call generates the whole story."""
    spec_with_outline.story_seed.chapter_outline = []
    agent = DraftStoryAgent(model="x", output_dir=tmp_path, word_count_target=2000)
    with patch.object(agent._model, "generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = "Once upon a time. " * 50
        story = await agent.generate_story(spec_with_outline)

    assert mock_gen.await_count == 1
    assert story.startswith("Once upon a time")


@pytest.mark.asyncio
async def test_chapter_prompt_includes_per_chapter_length_budget(spec_with_outline, tmp_path):
    """Each per-chapter call gets the 700-1100 word budget — bounded scope."""
    agent = DraftStoryAgent(model="x", output_dir=tmp_path, word_count_target=3000)
    with patch.object(agent._model, "generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = "p\n\n* * *\n\nv\n\n* * *\n"
        await agent.generate_story(spec_with_outline)

    for call in mock_gen.call_args_list:
        user = call.args[0]
        assert "700" in user
        assert "1100" in user
        assert "thematic poem" in user.lower()

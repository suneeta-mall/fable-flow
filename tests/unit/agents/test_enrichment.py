from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from fable_flow.agents.enrichment import (
    BiographyAgent,
    ExperimentDesignerAgent,
    ReflectionGeneratorAgent,
    enrich_chapters,
)
from fable_flow.schemas.book_content import Chapter
from fable_flow.schemas.input_spec import (
    Appearance,
    Character,
    CharacterRole,
    DedicatedPersonality,
    FableFlowInput,
    ProjectMetadata,
    StorySeed,
)


@pytest.fixture
def input_spec():
    return FableFlowInput(
        project=ProjectMetadata(title="T", target_age=6, genre="adv"),
        characters=[
            Character(
                name="Cassie",
                age=6,
                role=CharacterRole.PROTAGONIST,
                personality="curious",
                appearance=Appearance(
                    heritage="Indian Australian",
                    skin_tone="warm honey-brown",
                    hair="black",
                    eyes="brown",
                ),
                typical_clothing="dress",
            )
        ],
        story_seed=StorySeed(
            theme="tides",
            setting="beach",
            learning_objectives=["tides are caused by the moon"],
        ),
    )


@pytest.mark.asyncio
async def test_reflection_agent_produces_three_questions(input_spec):
    chapter = Chapter(
        number=1,
        title="Sunrise",
        text="Cassie woke up and watched the tide come in.",
        page_start=3,
        page_end=5,
    )
    agent = ReflectionGeneratorAgent(model="x")
    with patch.object(agent._model, "generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = (
            '["What did Cassie do first?",'
            ' "How do you think she felt about the tide?",'
            ' "Have you ever woken up early to see something special?"]'
        )
        result = await agent.generate_for_chapter(
            chapter, target_age=6, learning_objectives=input_spec.story_seed.learning_objectives
        )
    assert len(result.questions) == 3
    assert "Cassie" in result.questions[0]
    # Prompt must include the chapter text and the learning objectives.
    user_prompt = mock_gen.call_args.args[0]
    assert chapter.text in user_prompt
    assert "tides are caused by the moon" in user_prompt


@pytest.mark.asyncio
async def test_reflection_agent_rejects_wrong_count():
    chapter = Chapter(number=1, title="T", text="x", page_start=3, page_end=4)
    agent = ReflectionGeneratorAgent(model="x")
    with patch.object(agent._model, "generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = '["only one"]'
        with pytest.raises(ValueError, match="expected 3 questions"):
            await agent.generate_for_chapter(chapter, target_age=6, learning_objectives=[])


@pytest.mark.asyncio
async def test_experiment_designer(input_spec):
    agent = ExperimentDesignerAgent(model="x")
    payload = """{
        "title": "Tide in a Bowl",
        "concept": "Gravity makes water rise and fall.",
        "materials": ["bowl of water", "small magnet", "paper boat"],
        "steps": ["Fill bowl", "Float boat", "Move magnet near", "Watch boat move"],
        "what_to_observe": "The boat drifts toward the magnet, like the moon pulling tides.",
        "safety_note": "Adult should supervise with magnets."
    }"""
    with patch.object(agent._model, "generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = payload
        experiment = await agent.design(input_spec, "story body text here")

    assert experiment.title == "Tide in a Bowl"
    assert len(experiment.materials) == 3
    assert len(experiment.steps) == 4
    assert experiment.safety_note is not None


@pytest.mark.asyncio
async def test_experiment_designer_handles_null_safety(input_spec):
    agent = ExperimentDesignerAgent(model="x")
    payload = """{
        "title": "Salt Water",
        "concept": "Salt dissolves in water.",
        "materials": ["water", "salt", "spoon"],
        "steps": ["Pour water", "Add salt", "Stir", "Taste"],
        "what_to_observe": "The salt vanishes but the water tastes salty.",
        "safety_note": "null"
    }"""
    with patch.object(agent._model, "generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = payload
        experiment = await agent.design(input_spec, "story")
    assert experiment.safety_note is None


@pytest.mark.asyncio
async def test_biography_agent():
    person = DedicatedPersonality(
        name="Stephen Hawking",
        field="theoretical physics",
        notable_for="A Brief History of Time",
    )
    agent = BiographyAgent(model="x")
    payload = """{
        "name": "Stephen Hawking",
        "title": "Theoretical Physicist",
        "lifespan": "1942 – 2018",
        "one_line": "He helped us imagine the inside of a black hole.",
        "summary": "Stephen Hawking loved big questions...",
        "fun_facts": ["He wrote a famous book", "He was born 300 years after Galileo died", "He had a robot voice"],
        "why_inspiring": "He showed that curiosity can take you anywhere."
    }"""
    with patch.object(agent._model, "generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = payload
        bio = await agent.write(person, target_age=8)
    assert bio.name == "Stephen Hawking"
    assert bio.lifespan == "1942 – 2018"
    assert len(bio.fun_facts) == 3
    # Hints should be in the prompt
    user_prompt = mock_gen.call_args.args[0]
    assert "theoretical physics" in user_prompt
    assert "A Brief History of Time" in user_prompt


@pytest.mark.asyncio
async def test_biography_agent_handles_null_lifespan():
    person = DedicatedPersonality(name="Unknown Person")
    agent = BiographyAgent(model="x")
    payload = """{
        "name": "Unknown Person",
        "title": "Inventor",
        "lifespan": "unknown",
        "one_line": "x",
        "summary": "y",
        "fun_facts": ["a", "b", "c"],
        "why_inspiring": "z"
    }"""
    with patch.object(agent._model, "generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = payload
        bio = await agent.write(person, target_age=7)
    assert bio.lifespan is None


@pytest.mark.asyncio
async def test_enrich_chapters_populates_every_chapter(input_spec):
    chapters = [
        Chapter(number=1, title="A", text="t1", page_start=3, page_end=4),
        Chapter(number=2, title="B", text="t2", page_start=5, page_end=6),
    ]
    with patch("fable_flow.agents.enrichment.EnhancedTextModel") as mock_text_cls:
        mock_text_cls.return_value = AsyncMock()
        mock_text_cls.return_value.generate.return_value = '["q1?", "q2?", "q3?"]'
        result = await enrich_chapters(chapters, target_age=6, learning_objectives=[])
    assert all(c.reflection is not None for c in result)
    assert all(len(c.reflection.questions) == 3 for c in result)

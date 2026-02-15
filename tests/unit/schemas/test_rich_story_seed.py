"""Tests for the rich story_seed fields and back-compat coercions."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from fable_flow.schemas.input_spec import (
    Appearance,
    BackMatterPlan,
    ChapterOutlineItem,
    Character,
    CharacterRole,
    FableFlowInput,
    FeaturedMoment,
    ProjectMetadata,
    Setting,
    StorySeed,
    VocabularyWord,
)


def _minimal_characters():
    return [
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
    ]


def test_setting_accepts_plain_string():
    spec = FableFlowInput(
        project=ProjectMetadata(title="T", target_age=6, genre="adv"),
        characters=_minimal_characters(),
        story_seed=StorySeed(theme="t", setting="Sydney beach at sunrise"),
    )
    assert isinstance(spec.story_seed.setting, Setting)
    assert spec.story_seed.setting.primary == "Sydney beach at sunrise"
    assert spec.story_seed.setting.locations_visited == []


def test_setting_accepts_full_object():
    spec = FableFlowInput(
        project=ProjectMetadata(title="T", target_age=6, genre="adv"),
        characters=_minimal_characters(),
        story_seed=StorySeed(
            theme="t",
            setting={
                "primary": "Museum",
                "secondary": "train ride",
                "locations_visited": ["pixel wall", "see-and-say booth"],
            },
        ),
    )
    assert spec.story_seed.setting.primary == "Museum"
    assert spec.story_seed.setting.secondary == "train ride"
    assert "pixel wall" in spec.story_seed.setting.locations_visited


def test_empty_setting_string_rejected():
    with pytest.raises(ValidationError):
        StorySeed(theme="t", setting="   ")


def test_rich_seed_fields_all_optional():
    """Existing minimal inputs should still validate."""
    seed = StorySeed(theme="theme", setting="beach")
    assert seed.premise is None
    assert seed.tone_and_voice is None
    assert seed.recurring_motifs == []
    assert seed.vocabulary_introduced == []
    assert seed.chapter_outline == []
    assert seed.featured_moment is None
    assert seed.dedication_text is None
    assert seed.back_matter is None


def test_rich_seed_fields_round_trip():
    seed = StorySeed(
        theme="t",
        setting="beach",
        premise="A girl learns about tides.",
        tone_and_voice="warm, playful",
        recurring_motifs=["water", "wonder"],
        vocabulary_introduced=[
            VocabularyWord(word="tide", kid_friendly_meaning="the rise and fall of the sea"),
        ],
        story_arc={"act_1": "curiosity", "act_2": "discovery"},
        chapter_outline=[
            ChapterOutlineItem(number=1, title="Morning", beats="She wakes up early"),
            ChapterOutlineItem(
                number=2, title="Beach", beats="She finds tide pools", introduces="tides"
            ),
        ],
        featured_moment=FeaturedMoment(
            where="Chapter 2",
            purpose="key discovery",
            core_message="tides are caused by the moon",
            draft_text="And then she saw the moon...",
        ),
        dedication_text="For Rachel Carson.",
        back_matter=BackMatterPlan(
            for_kids="Try sorting shells",
            for_parents="Read together",
            extended_biography="Rachel was born in 1907...",
        ),
    )
    dumped = seed.model_dump()
    rehydrated = StorySeed.model_validate(dumped)
    assert rehydrated.premise == "A girl learns about tides."
    assert len(rehydrated.chapter_outline) == 2
    assert rehydrated.chapter_outline[1].introduces == "tides"
    assert rehydrated.featured_moment.draft_text.startswith("And then")
    assert rehydrated.back_matter.for_kids == "Try sorting shells"


def test_project_metadata_new_optional_fields():
    project = ProjectMetadata(
        title="T",
        subtitle="A subtitle",
        target_age=7,
        age_range="5-10",
        genre="adv",
        tagline="A short tagline",
    )
    assert project.subtitle == "A subtitle"
    assert project.age_range == "5-10"
    assert project.tagline == "A short tagline"


def test_dedicated_personality_why_field():
    from fable_flow.schemas.input_spec import DedicatedPersonality

    person = DedicatedPersonality(
        name="Fei-Fei Li",
        field="computer science",
        notable_for="ImageNet",
        why_this_dedication="She paid attention to how children learn",
    )
    assert person.why_this_dedication.startswith("She paid attention")


def test_fei_fei_example_file_parses():
    """The shipped Fei-Fei example must load with no errors."""
    spec = FableFlowInput.from_json_file("examples/cassie_fei_fei_li_input.json")
    assert spec.project.title.startswith("Cassie, Caleb")
    assert spec.project.volume == 4
    assert spec.project.subtitle == "How Computers Came to See the World"
    assert spec.story_seed.setting.primary.startswith("Sydney Powerhouse")
    assert len(spec.story_seed.setting.locations_visited) == 5
    assert len(spec.story_seed.chapter_outline) == 8
    assert spec.story_seed.featured_moment is not None
    assert spec.story_seed.back_matter.for_parents is not None
    assert spec.dedicated_to.why_this_dedication is not None

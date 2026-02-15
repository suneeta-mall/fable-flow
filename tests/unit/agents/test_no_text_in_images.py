"""All image prompts must lead with the NO_TEXT directive.

Diffusion models weight early tokens more heavily, and FLUX (the default image
model) has no negative-prompt parameter — so suppressing text artifacts in the
generated image relies on this directive being PREPENDED to every prompt.
"""

from __future__ import annotations

import pytest

from fable_flow.agents._image_prompts import (
    NO_TEXT_DIRECTIVE,
    build_full_body_prompt,
    build_negative_prompt,
    build_portrait_prompt,
    build_scene_prompt,
    build_scene_prompt_for_movie,
)
from fable_flow.agents.cover_designer import _build_back_prompt, _build_front_prompt
from fable_flow.schemas.book_content import (
    BookContent,
    BookMetadata,
    Chapter,
    CharacterReference,
    IllustrationSpec,
)
from fable_flow.schemas.input_spec import (
    Appearance,
    Character,
    CharacterRole,
)


@pytest.fixture
def character():
    return Character(
        name="Cassie",
        age=6,
        role=CharacterRole.PROTAGONIST,
        personality="curious",
        appearance=Appearance(heritage="X", skin_tone="warm", hair="black", eyes="brown"),
        typical_clothing="dress",
    )


@pytest.fixture
def book():
    return BookContent(
        metadata=BookMetadata(
            title="Cassie's Book",
            subtitle="A subtitle",
            tagline="A tagline.",
            target_age=8,
            page_count=10,
            genre="adventure",
        ),
        chapters=[Chapter(number=1, title="C", text="t", page_start=3, page_end=4)],
        full_text="t",
        characters_used=["Cassie"],
        character_references=[CharacterReference(name="Cassie", portrait_path="/tmp/x.png")],
    )


# ----- POSITIVE PROMPTS LEAD WITH ANTI-TEXT DIRECTIVE ----------------------


def test_no_text_directive_explicitly_lists_artifacts():
    """Sanity: the shared directive itself names the specific artifacts to suppress."""
    for term in (
        "no text",
        "no letters",
        "no words",
        "no typography",
        "no captions",
        "no watermarks",
        "no logos",
    ):
        assert term.lower() in NO_TEXT_DIRECTIVE.lower(), f"missing {term!r}"


def test_portrait_prompt_leads_with_no_text_directive(character):
    prompt = build_portrait_prompt(character, illustration_style="watercolor")
    assert prompt.startswith(NO_TEXT_DIRECTIVE)


def test_full_body_prompt_leads_with_no_text_directive(character):
    prompt = build_full_body_prompt(character, illustration_style="watercolor")
    assert prompt.startswith(NO_TEXT_DIRECTIVE)


def test_scene_prompt_leads_with_no_text_directive(character):
    spec = IllustrationSpec(
        page=4,
        placement="inline",
        description="Cassie at the beach",
        characters=["Cassie"],
        scene_context="morning",
    )
    prompt = build_scene_prompt(spec, [character], illustration_style="watercolor")
    assert prompt.startswith(NO_TEXT_DIRECTIVE)


def test_movie_scene_prompt_leads_with_no_text_directive(character):
    prompt = build_scene_prompt_for_movie(
        scene_text="Cassie steps into the surf",
        setting="beach",
        mood="curious",
        characters_in_scene=["Cassie"],
        full_cast=[character],
        illustration_style="watercolor",
    )
    assert prompt.startswith(NO_TEXT_DIRECTIVE)


def test_cover_front_prompt_leads_with_no_text_directive(book):
    prompt = _build_front_prompt(book)
    assert prompt.startswith(NO_TEXT_DIRECTIVE)


def test_cover_back_prompt_leads_with_no_text_directive(book):
    prompt = _build_back_prompt(book)
    assert prompt.startswith(NO_TEXT_DIRECTIVE)


# ----- NEGATIVE PROMPT COVERS TEXT-SPECIFIC TERMS --------------------------


def test_negative_prompt_lists_text_specific_terms():
    """SDXL/SD3 negative prompt should reject text-rendering artifacts explicitly."""
    neg = build_negative_prompt(target_age=8).lower()
    for term in (
        "text",
        "letters",
        "words",
        "typography",
        "watermarks",
        "logos",
        "signatures",
        "writing",
    ):
        assert term in neg, f"negative prompt missing {term!r}"


def test_negative_prompt_still_includes_safety_terms():
    """Adding text suppression must not remove the existing safety negatives."""
    neg = build_negative_prompt(target_age=8).lower()
    for term in ("scary", "violence", "deformed", "8-year-old"):
        assert term in neg


# ----- COVER PROMPTS DON'T CONTAIN POSITIVE TEXT-LIKE PHRASES --------------


def test_cover_prompts_avoid_phrases_that_could_imply_text_in_image(book):
    """The prompts must not contain phrases a diffusion model might read as 'add text'.

    Examples of bad wording: 'with title rendered', 'show the title', 'banner saying'.
    Title is mentioned as subject context only ('for the story X') — never as
    something to draw.
    """
    bad_substrings = [
        "render the title",
        "show the title",
        "banner saying",
        "title text",
        "draw the title",
        "with text",
    ]
    for prompt in (_build_front_prompt(book), _build_back_prompt(book)):
        lower = prompt.lower()
        for bad in bad_substrings:
            assert bad not in lower, f"prompt contains {bad!r}"

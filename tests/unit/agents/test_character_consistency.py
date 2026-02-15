"""Character consistency: identity anchors + ref images + IP-Adapter dispatch."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from fable_flow.agents._image_prompts import (
    build_full_body_prompt,
    build_identity_block,
    build_negative_prompt,
    build_portrait_prompt,
    build_scene_prompt,
    build_style_anchor,
)
from fable_flow.agents.book_assembly import IllustrationGeneratorAgent
from fable_flow.agents.character_ref import CharacterReferenceAgent
from fable_flow.schemas.book_content import Chapter, CharacterReference, IllustrationSpec
from fable_flow.schemas.input_spec import (
    Appearance,
    Character,
    CharacterRole,
)


@pytest.fixture
def cassie():
    return Character(
        name="Cassie",
        age=6,
        role=CharacterRole.PROTAGONIST,
        personality="curious",
        appearance=Appearance(
            heritage="Indian Australian",
            skin_tone="warm honey-brown",
            hair="wavy black",
            eyes="bright brown",
            distinctive_features=["wide smile"],
        ),
        typical_clothing="colourful sundress",
    )


@pytest.fixture
def caleb():
    return Character(
        name="Caleb",
        age=3,
        role=CharacterRole.SUPPORTING,
        personality="playful",
        appearance=Appearance(
            heritage="Indian Australian",
            skin_tone="warm honey-brown",
            hair="curly black",
            eyes="brown",
        ),
        typical_clothing="striped t-shirt",
    )


def test_identity_block_is_deterministic(cassie):
    """Same character → identical text every call (no whitespace variation)."""
    assert build_identity_block(cassie) == build_identity_block(cassie)
    block = build_identity_block(cassie)
    assert "Cassie" in block
    assert "6-year-old" in block
    assert "warm honey-brown" in block
    assert "wavy black hair" in block
    assert "wide smile" in block
    assert "colourful sundress" in block


def test_identity_block_drops_age_when_missing():
    char = Character(
        name="Narrator",
        role=CharacterRole.MINOR,
        personality="warm",
        appearance=Appearance(heritage="Generic", skin_tone="fair", hair="grey", eyes="hazel"),
        typical_clothing="cardigan",
    )
    block = build_identity_block(char)
    assert "year-old" not in block
    assert "Narrator" in block


def test_scene_prompt_orders_identity_before_style(cassie, caleb):
    spec = IllustrationSpec(
        page=4,
        placement="full_page",
        description="At the kitchen table eating breakfast",
        characters=["Cassie", "Caleb"],
        scene_context="morning, kitchen",
    )
    prompt = build_scene_prompt(spec, [cassie, caleb], "digital watercolour", motifs=["pixels"])

    identity_idx = prompt.find("Cassie")
    style_idx = prompt.find("Art style")
    motifs_idx = prompt.find("pixels")
    assert 0 <= identity_idx < style_idx
    assert identity_idx < motifs_idx
    # Both characters' identity blocks are present
    assert "Caleb" in prompt
    assert "warm honey-brown" in prompt
    # Scene description and setting included
    assert "kitchen table eating breakfast" in prompt
    assert "morning, kitchen" in prompt


def test_scene_prompt_with_no_known_characters_still_works(cassie):
    """Scene refers to characters not in the cast — block is omitted, prompt still has the scene."""
    spec = IllustrationSpec(
        page=4,
        placement="inline",
        description="A pigeon lands on the railing",
        characters=["RandomPigeon"],  # not in cast
        scene_context="evening, harbour",
    )
    prompt = build_scene_prompt(spec, [cassie], "digital watercolour")
    assert "pigeon" in prompt.lower()
    # The identity-anchor block is skipped entirely (avoids stale info)
    assert "Cassie" not in prompt


def test_portrait_and_full_body_prompts_use_same_identity(cassie):
    portrait = build_portrait_prompt(cassie, "digital watercolour")
    full = build_full_body_prompt(cassie, "digital watercolour")
    identity = build_identity_block(cassie)
    assert identity in portrait
    assert identity in full
    assert "Centered head-and-shoulders" in portrait
    assert "full body" in full.lower()


def test_negative_prompt_targets_age(caleb):
    neg = build_negative_prompt(target_age=6)
    assert "6-year-old" in neg
    assert "blurry" in neg


def test_style_anchor_omits_motifs_section_when_empty():
    with_motifs = build_style_anchor("watercolour", ["motif1", "motif2"])
    without = build_style_anchor("watercolour", [])
    assert "motif1" in with_motifs
    assert "motif" not in without


@pytest.mark.asyncio
async def test_character_reference_agent_renders_two_views_per_char(cassie, caleb, tmp_path):
    image_model = AsyncMock()
    image_model.generate_image = AsyncMock(return_value=b"PNG_BYTES")

    agent = CharacterReferenceAgent(image_model=image_model, output_dir=tmp_path)
    refs = await agent.generate_all([cassie, caleb])

    assert len(refs) == 2
    assert {r.name for r in refs} == {"Cassie", "Caleb"}
    for r in refs:
        assert (
            r.portrait_path
            and (tmp_path / "character_refs").joinpath(f"{r.name.lower()}_portrait.png").exists()
        )
        assert (
            r.full_body_path
            and (tmp_path / "character_refs").joinpath(f"{r.name.lower()}_full.png").exists()
        )
    # 2 chars × 2 views = 4 calls
    assert image_model.generate_image.await_count == 4


@pytest.mark.asyncio
async def test_character_reference_agent_skips_minor_roles(cassie, tmp_path):
    minor = Character(
        name="Background",
        role=CharacterRole.MINOR,
        personality="quiet",
        appearance=Appearance(heritage="X", skin_tone="y", hair="z", eyes="w"),
        typical_clothing="grey",
    )
    image_model = AsyncMock()
    image_model.generate_image = AsyncMock(return_value=b"PNG")
    refs = await CharacterReferenceAgent(image_model, output_dir=tmp_path).generate_all(
        [cassie, minor], resume=False
    )
    assert [r.name for r in refs] == ["Cassie"]


@pytest.mark.asyncio
async def test_character_reference_agent_resume_skips_existing(cassie, tmp_path):
    refs_dir = tmp_path / "character_refs"
    refs_dir.mkdir(parents=True)
    (refs_dir / "cassie_portrait.png").write_bytes(b"existing")
    (refs_dir / "cassie_full.png").write_bytes(b"existing")

    image_model = AsyncMock()
    image_model.generate_image = AsyncMock(return_value=b"NEW")
    refs = await CharacterReferenceAgent(image_model, output_dir=tmp_path).generate_all(
        [cassie], resume=True
    )
    assert image_model.generate_image.await_count == 0
    assert refs[0].portrait_path
    assert (refs_dir / "cassie_portrait.png").read_bytes() == b"existing"


@pytest.mark.asyncio
async def test_illustration_generator_uses_ip_adapter_when_ref_available(cassie, tmp_path):
    """When a character ref exists for a scene character, IP-Adapter path is taken."""
    chapters = [
        Chapter(
            number=1,
            title="A",
            text="x",
            page_start=3,
            page_end=4,
            illustrations=[
                IllustrationSpec(
                    page=4,
                    placement="full_page",
                    description="Cassie at sunrise",
                    characters=["Cassie"],
                    scene_context="morning, window",
                )
            ],
        )
    ]
    refs_dir = tmp_path / "character_refs"
    refs_dir.mkdir(parents=True)
    portrait = refs_dir / "cassie_portrait.png"
    portrait.write_bytes(b"PORTRAIT")
    character_refs = [CharacterReference(name="Cassie", portrait_path=str(portrait))]

    image_model = AsyncMock()
    image_model.generate_with_reference = AsyncMock(return_value=b"NEW")
    image_model.generate_image = AsyncMock(return_value=b"NEW")

    agent = IllustrationGeneratorAgent(image_model, output_dir=tmp_path)
    await agent.generate_all(chapters, [cassie], character_refs=character_refs, target_age=6)

    # IP-Adapter path used; plain path not used
    image_model.generate_with_reference.assert_awaited_once()
    image_model.generate_image.assert_not_awaited()
    call_kwargs = image_model.generate_with_reference.call_args.kwargs
    assert call_kwargs["reference_image_path"] == str(portrait)
    # Identity anchor and negative prompt both threaded through
    assert "warm honey-brown" in call_kwargs["prompt"]
    assert "6-year-old" in call_kwargs["negative_prompt"]


@pytest.mark.asyncio
async def test_illustration_generator_falls_back_to_text_only_when_no_ref(cassie, tmp_path):
    chapters = [
        Chapter(
            number=1,
            title="A",
            text="x",
            page_start=3,
            page_end=4,
            illustrations=[
                IllustrationSpec(
                    page=4,
                    placement="full_page",
                    description="A scene",
                    characters=["UnknownChar"],  # no ref available
                    scene_context="x",
                )
            ],
        )
    ]
    image_model = AsyncMock()
    image_model.generate_image = AsyncMock(return_value=b"NEW")
    image_model.generate_with_reference = AsyncMock(return_value=b"NEW")

    agent = IllustrationGeneratorAgent(image_model, output_dir=tmp_path)
    await agent.generate_all(chapters, [cassie], character_refs=[], target_age=6)

    image_model.generate_image.assert_awaited_once()
    image_model.generate_with_reference.assert_not_awaited()

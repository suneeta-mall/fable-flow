"""Cover designer: deterministic generation + PIL text overlay + resume."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from PIL import Image, ImageFont

from fable_flow.agents.cover_designer import (
    COVER_HEIGHT,
    COVER_WIDTH,
    CoverDesignerAgent,
    _build_back_prompt,
    _build_front_prompt,
    _compose_back_blurb,
    _load_font,
    _stable_seed,
)
from fable_flow.schemas.book_content import (
    Biography,
    BookContent,
    BookMetadata,
    Chapter,
    CharacterReference,
    Experiment,
)
from fable_flow.schemas.input_spec import (
    Appearance,
    Character,
    CharacterRole,
)


def _cassie_character() -> Character:
    return Character(
        name="Cassie",
        age=7,
        role=CharacterRole.PROTAGONIST,
        personality="curious, observant",
        appearance=Appearance(
            heritage="Indian-Australian",
            skin_tone="warm brown",
            hair="long black",
            eyes="dark brown",
            distinctive_features=["small star-shaped freckle on left cheek"],
        ),
        typical_clothing="yellow sundress",
    )


def _supporting_character() -> Character:
    return Character(
        name="Mum",
        age=35,
        role=CharacterRole.SUPPORTING,
        personality="patient",
        appearance=Appearance(
            heritage="Indian-Australian",
            skin_tone="warm brown",
            hair="black bob",
            eyes="dark brown",
        ),
        typical_clothing="linen kurta",
    )


def _biography() -> Biography:
    return Biography(
        name="Fei-Fei Li",
        title="Computer Scientist",
        lifespan="1976 –",
        one_line="she taught computers to see",
        summary="Fei-Fei grew up in Chengdu and studied physics at Princeton.",
        fun_facts=["Led Stanford AI Lab", "Co-founded AI4ALL", "Wrote The Worlds I See"],
        why_inspiring="She asked audacious questions about what machines could learn.",
    )


def _book(**overrides) -> BookContent:
    metadata_kwargs = {
        "title": "Cassie and the Eye That Learned to See",
        "subtitle": "A Story for the Curious",
        "tagline": "Some questions are very small.",
        "series": "The Curious Cassie Collection",
        "volume": 4,
        "target_age": 8,
        "page_count": 24,
        "genre": "adventure",
        "premise": "When Cassie wonders what makes a banana a banana, she finds out.",
    }
    metadata_kwargs.update(overrides.pop("metadata", {}))
    return BookContent(
        metadata=BookMetadata(**metadata_kwargs),
        chapters=[Chapter(number=1, title="Start", text="prose", page_start=3, page_end=4)],
        full_text="combined text",
        characters_used=["Cassie"],
        character_references=[CharacterReference(name="Cassie", portrait_path="/tmp/cassie.png")],
        **overrides,
    )


def _png_bytes(color: str = "#88AAFF") -> bytes:
    buf = BytesIO()
    Image.new("RGB", (COVER_WIDTH, COVER_HEIGHT), color=color).save(buf, format="PNG")
    return buf.getvalue()


# ----- DETERMINISM ----------------------------------------------------------


def test_stable_seed_is_deterministic():
    assert _stable_seed("X") == _stable_seed("X")
    assert _stable_seed("X") != _stable_seed("Y")


def test_front_and_back_prompts_use_different_seeds():
    """Same title must give different front vs back seeds so the artwork differs."""
    title = "My Book"
    assert _stable_seed(title) != _stable_seed(title + "::back")


def test_front_prompt_excludes_text_artifacts():
    """Generated illustration must NOT contain text — that's all overlaid later."""
    book = _book()
    prompt = _build_front_prompt(book)
    lower = prompt.lower()
    assert "no text" in lower
    assert "no letters" in lower
    assert "no typography" in lower


def test_front_prompt_omits_book_title_verbatim():
    """The title MUST NOT appear in the diffusion prompt — quoting it makes
    the model try to render it as text. Title is added by PIL overlay only."""
    book = _book()
    prompt = _build_front_prompt(book)
    assert book.metadata.title not in prompt


def test_front_prompt_omits_trigger_words_book_and_cover():
    """'book cover' as a format word is the single strongest text-rendering
    trigger in diffusion models. It must NEVER appear in the prompt.

    Standalone 'book' / 'cover' words are checked with word boundaries so
    incidental occurrences inside compounds (e.g. 'notebooks') don't trip the
    test — only the standalone trigger form is forbidden.
    """
    import re

    book = _book(biography=_biography())
    prompt = _build_front_prompt(book, protagonist=_cassie_character()).lower()
    assert "book cover" not in prompt
    assert re.search(r"\bbook\b", prompt) is None
    assert re.search(r"\bcover\b", prompt) is None
    assert re.search(r"\bmagazine\b", prompt) is None
    assert re.search(r"\bmovie poster\b", prompt) is None


def test_back_prompt_omits_trigger_words_book_and_cover():
    import re

    book = _book()
    prompt = _build_back_prompt(book).lower()
    assert "book cover" not in prompt
    assert re.search(r"\bbook\b", prompt) is None
    assert re.search(r"\bcover\b", prompt) is None


def test_front_prompt_excludes_text_bearing_objects():
    """Common diffusion failure modes: text appears on signs, screens, books
    inside the scene. Prompt must explicitly exclude those surfaces."""
    book = _book()
    prompt = _build_front_prompt(book).lower()
    for obj in ("signs", "banners", "posters", "scrolls", "screens", "chalkboards"):
        assert obj in prompt, f"prompt should mention {obj!r} as excluded"


def test_back_prompt_excludes_text_bearing_objects():
    book = _book()
    prompt = _build_back_prompt(book).lower()
    for obj in ("signs", "banners", "posters", "scrolls", "screens"):
        assert obj in prompt


def test_front_prompt_frames_as_wordless_painting():
    """Image format anchoring: 'wordless painting' / 'art print' have no
    learned text-content prior, unlike 'book cover' which strongly does."""
    book = _book()
    prompt = _build_front_prompt(book).lower()
    assert "wordless" in prompt
    assert "painting" in prompt or "art print" in prompt


# ----- FRONT/BACK VISUAL CONSISTENCY ---------------------------------------


def test_front_and_back_use_same_visual_context_clause():
    """Both covers must use the EXACT same palette + lighting + style + setting
    clause — same words to the model produces the same palette out."""
    from fable_flow.agents.cover_designer import _shared_visual_context

    book = _book(biography=_biography())
    shared = _shared_visual_context(book)
    front = _build_front_prompt(book, protagonist=_cassie_character())
    back = _build_back_prompt(book)
    assert shared in front
    assert shared in back


def test_shared_visual_context_includes_palette_and_setting():
    """Sanity: the shared clause covers palette, lighting, style, and setting."""
    from fable_flow.agents.cover_designer import _shared_visual_context

    book = _book(biography=_biography())
    shared = _shared_visual_context(book).lower()
    assert "palette" in shared
    assert "lighting" in shared
    assert "watercolor" in shared or "painterly" in shared
    # Setting/world anchor is derived from biography.one_line when present
    assert "taught computers to see" in shared


def test_back_prompt_declares_itself_companion_to_front():
    """Back prompt must explicitly tell the model this is a companion piece
    extending the front — otherwise the model produces an unrelated landscape
    with a different palette."""
    book = _book()
    prompt = _build_back_prompt(book).lower()
    assert "companion" in prompt
    assert "same colour palette" in prompt or "same palette" in prompt
    assert "same painted world" in prompt or "same world" in prompt


def test_back_prompt_does_not_reverse_palette_to_desaturated():
    """Regression: the old back prompt asked for 'soft slightly desaturated'
    while the front asked for 'rich saturated' — opposite palettes produce
    visually unrelated covers. The shared clause forbids that."""
    book = _book()
    prompt = _build_back_prompt(book).lower()
    assert "desaturated" not in prompt


def test_back_prompt_keeps_characters_distant_or_absent():
    """The back is a landscape, not a portrait — characters should be absent
    or only small distant figures so the blurb overlay has clean space."""
    book = _book()
    prompt = _build_back_prompt(book).lower()
    assert "distant" in prompt or "absent" in prompt
    assert "landscape" in prompt or "establishing" in prompt


# ----- COVER FEATURES PROTAGONIST + BIOGRAPHY ------------------------------


def test_front_prompt_names_explicit_protagonist():
    """When a `Character` is given, its name appears in the protagonist clause."""
    book = _book()
    prompt = _build_front_prompt(book, protagonist=_cassie_character())
    assert "Cassie" in prompt
    assert "the protagonist" in prompt


def test_front_prompt_falls_back_to_first_character_ref_when_no_character():
    """No Character object → uses the first character_references entry by name."""
    book = _book()  # has CharacterReference(name="Cassie")
    prompt = _build_front_prompt(book, protagonist=None)
    assert "young child named Cassie" in prompt


def test_front_prompt_folds_in_character_appearance():
    """The Character's heritage / skin tone / hair / eyes / clothing MUST appear
    in the prompt — that's what makes the cover protagonist look like the
    in-book character rather than a generic kid."""
    book = _book()
    prompt = _build_front_prompt(book, protagonist=_cassie_character())
    for needle in (
        "Indian-Australian",
        "warm brown",  # skin tone
        "long black",  # hair
        "dark brown",  # eyes
        "yellow sundress",  # clothing
        "star-shaped freckle",  # distinctive feature
    ):
        assert needle in prompt, f"appearance field missing from prompt: {needle!r}"


def test_front_prompt_locks_appearance_match_to_identity_block():
    """The prompt must instruct the model to match the identity description
    exactly — otherwise FLUX may follow the activity description more strongly
    than the identity."""
    book = _book()
    prompt = _build_front_prompt(book, protagonist=_cassie_character()).lower()
    assert "must match" in prompt
    assert "identity description" in prompt
    # Mentions consistency with the reference image (IP-Adapter conditioning)
    assert "reference image" in prompt


def test_front_prompt_includes_biography_subject_when_present():
    """When `book.biography` is set, the cover must show that figure too."""
    book = _book(biography=_biography())
    prompt = _build_front_prompt(book, protagonist=_cassie_character())
    assert "Fei-Fei Li" in prompt
    assert "Computer Scientist" in prompt
    # Both characters appear together
    assert "the two of them" in prompt.lower() or "together with" in prompt.lower()
    # Biography one-liner gives the model a concrete activity to depict
    assert "taught computers to see" in prompt
    # AND the protagonist's appearance is still present (not overshadowed)
    assert "Indian-Australian" in prompt


def test_front_prompt_omits_biography_block_when_absent():
    """No biography → fall back to single-character cover (no 'TWO characters')."""
    book = _book(biography=None)
    prompt = _build_front_prompt(book, protagonist=_cassie_character())
    assert "TWO characters" not in prompt
    assert "Cassie" in prompt


def test_front_prompt_uses_biography_oneliner_as_topic_when_present():
    """Biography's one-liner is a richer 'visual topic' than a generic mood word."""
    book = _book(biography=_biography())
    prompt = _build_front_prompt(book, protagonist=_cassie_character())
    # The biography one-line drives the topic anchor
    assert "taught computers to see" in prompt
    # Topic anchor phrasing
    assert "topic" in prompt.lower() or "activity" in prompt.lower()


def test_front_prompt_topic_falls_back_to_subtitle_without_biography():
    """No biography one-liner → subtitle is the topic anchor."""
    book = _book(biography=None, metadata={"subtitle": "A Story for the Curious"})
    prompt = _build_front_prompt(book, protagonist=_cassie_character())
    assert "A Story for the Curious" in prompt


@pytest.mark.asyncio
async def test_design_covers_threads_character_appearance_into_prompt(tmp_path):
    """The agent must thread Character appearance into the front-cover prompt.

    Sets up a real portrait file on disk so the FRONT goes through
    `generate_with_reference` (call[0] = front, call[1] = back). The front
    prompt must carry the protagonist's appearance + biography fields.
    """
    image_model = MagicMock()
    image_model.generate_image = AsyncMock(return_value=_png_bytes())
    image_model.generate_with_reference = AsyncMock(return_value=_png_bytes())

    portrait_path = tmp_path / "cassie_portrait.png"
    Image.new("RGB", (256, 256)).save(portrait_path)
    book = _book(biography=_biography())
    book.character_references = [
        CharacterReference(name="Cassie", portrait_path=str(portrait_path))
    ]

    agent = CoverDesignerAgent(image_model, output_dir=tmp_path)
    await agent.design_covers(
        book,
        characters=[_cassie_character(), _supporting_character()],
        protagonist_name="Cassie",
    )

    # Front is the first generate_with_reference call (back is the second).
    front_prompt = image_model.generate_with_reference.call_args_list[0].kwargs["prompt"]
    assert "Cassie" in front_prompt
    assert "Indian-Australian" in front_prompt
    assert "yellow sundress" in front_prompt
    assert "Fei-Fei Li" in front_prompt


@pytest.mark.asyncio
async def test_design_covers_uses_portrait_reference_when_available(tmp_path):
    """When the protagonist has a portrait_path on disk, the front-cover call
    must go through `generate_with_reference` (IP-Adapter / FLUX 2 native) so
    the character likeness transfers visually, not just textually."""
    image_model = MagicMock()
    image_model.generate_image = AsyncMock(return_value=_png_bytes())
    image_model.generate_with_reference = AsyncMock(return_value=_png_bytes())

    # Create a real portrait file on disk so the path check passes.
    portrait_path = tmp_path / "cassie_portrait.png"
    Image.new("RGB", (256, 256)).save(portrait_path)

    book = _book()
    book.character_references = [
        CharacterReference(name="Cassie", portrait_path=str(portrait_path))
    ]

    agent = CoverDesignerAgent(image_model, output_dir=tmp_path)
    await agent.design_covers(book, characters=[_cassie_character()], protagonist_name="Cassie")

    # Both front and back use generate_with_reference: front conditions on the
    # protagonist portrait, back conditions on the just-generated front_base.
    assert image_model.generate_with_reference.call_count == 2
    front_call = image_model.generate_with_reference.call_args_list[0]
    assert front_call.kwargs["reference_image_path"] == str(portrait_path)
    back_call = image_model.generate_with_reference.call_args_list[1]
    assert Path(back_call.kwargs["reference_image_path"]).name == "front_base.png"
    # Plain generate_image is not used at all in this path.
    assert not image_model.generate_image.called


@pytest.mark.asyncio
async def test_design_covers_falls_back_to_plain_generate_without_portrait(tmp_path):
    """No portrait reference → front uses plain `generate_image`. Back STILL
    uses `generate_with_reference` because front_base exists by then."""
    image_model = MagicMock()
    image_model.generate_image = AsyncMock(return_value=_png_bytes())
    image_model.generate_with_reference = AsyncMock(return_value=_png_bytes())

    book = _book()
    # character_references entry exists but the path doesn't resolve to a file
    book.character_references = [
        CharacterReference(name="Cassie", portrait_path="/nonexistent/cassie.png")
    ]

    agent = CoverDesignerAgent(image_model, output_dir=tmp_path)
    await agent.design_covers(book, characters=[_cassie_character()])

    # Front: 1 plain call (no portrait). Back: 1 reference call (on front_base).
    assert image_model.generate_image.call_count == 1
    assert image_model.generate_with_reference.call_count == 1
    back_call = image_model.generate_with_reference.call_args_list[0]
    assert Path(back_call.kwargs["reference_image_path"]).name == "front_base.png"


def test_resolve_protagonist_prefers_explicit_name():
    chars = [_supporting_character(), _cassie_character()]  # protagonist NOT first
    resolved = CoverDesignerAgent._resolve_protagonist(_book(), chars, "Cassie")
    assert resolved is not None and resolved.name == "Cassie"


def test_resolve_protagonist_falls_back_to_role():
    chars = [_supporting_character(), _cassie_character()]
    # No explicit name: should find the CharacterRole.PROTAGONIST
    resolved = CoverDesignerAgent._resolve_protagonist(_book(), chars, None)
    assert resolved is not None and resolved.name == "Cassie"


def test_resolve_protagonist_returns_none_when_no_characters():
    resolved = CoverDesignerAgent._resolve_protagonist(_book(), None, "Cassie")
    assert resolved is None


def test_back_prompt_reserves_overlay_space():
    """Back-cover prompt must signal uncluttered area for text overlay."""
    book = _book()
    prompt = _build_back_prompt(book)
    lower = prompt.lower()
    assert "no text" in lower
    assert "overlay" in lower or "uncluttered" in lower


# ----- BACK-COVER BLURB COMPOSITION ----------------------------------------


def test_compose_back_blurb_uses_tagline_and_premise():
    book = _book()
    blocks = _compose_back_blurb(book)
    assert any("Some questions are very small" in b for b in blocks)
    assert any("Cassie wonders" in b for b in blocks)
    assert any("8-year-old" in b for b in blocks)
    assert any("Volume 4" in b for b in blocks)


def test_compose_back_blurb_falls_back_to_subtitle_when_no_premise():
    book = _book(metadata={"premise": None})
    blocks = _compose_back_blurb(book)
    assert any("A Story for the Curious" in b for b in blocks)


def test_compose_back_blurb_skips_missing_optional_fields():
    book = _book(
        metadata={
            "tagline": None,
            "premise": None,
            "subtitle": None,
            "series": None,
            "volume": None,
        }
    )
    blocks = _compose_back_blurb(book)
    # Only audience line remains; no series/volume/tagline/premise/subtitle lines
    assert len(blocks) == 1
    assert "8-year-old" in blocks[0]


# ----- AGENT BEHAVIOUR ------------------------------------------------------


@pytest.mark.asyncio
async def test_design_covers_generates_and_overlays(tmp_path):
    """Happy path: generates front + back, composites text, writes 4 PNGs.

    No protagonist Character → front uses plain `generate_image`. Back ALWAYS
    uses `generate_with_reference` with the front_base as the conditioning
    reference for palette / style continuity.
    """
    image_model = MagicMock()
    image_model.generate_image = AsyncMock(return_value=_png_bytes("#446688"))
    image_model.generate_with_reference = AsyncMock(return_value=_png_bytes("#88AA66"))

    agent = CoverDesignerAgent(image_model, output_dir=tmp_path)
    cover = await agent.design_covers(_book())

    # All four files (front_base, back_base, front, back) exist
    for path in (cover.front_path, cover.back_path, cover.front_base_path, cover.back_base_path):
        assert path is not None and Path(path).exists()
    # Composited covers are PNGs and have the cover dimensions
    front = Image.open(cover.front_path)
    assert front.size == (COVER_WIDTH, COVER_HEIGHT)
    # Front: 1 plain call. Back: 1 reference-conditioned call on front_base.
    assert image_model.generate_image.call_count == 1
    assert image_model.generate_with_reference.call_count == 1


@pytest.mark.asyncio
async def test_design_covers_uses_stable_seed_per_book(tmp_path):
    """Seeds for front and back are deterministically derived from the book title."""
    image_model = MagicMock()
    image_model.generate_image = AsyncMock(return_value=_png_bytes())
    image_model.generate_with_reference = AsyncMock(return_value=_png_bytes())

    book = _book()
    agent = CoverDesignerAgent(image_model, output_dir=tmp_path)
    await agent.design_covers(book)

    front_seed = image_model.generate_image.call_args_list[0].kwargs["seed"]
    back_seed = image_model.generate_with_reference.call_args_list[0].kwargs["seed"]
    seeds = [front_seed, back_seed]
    assert len(seeds) == 2
    assert seeds[0] != seeds[1]
    assert seeds[0] == _stable_seed(book.metadata.title)
    assert seeds[1] == _stable_seed(book.metadata.title + "::back")


@pytest.mark.asyncio
async def test_design_covers_resume_skips_when_final_files_exist(tmp_path):
    """resume=True with both composited files present → no image-model calls."""
    image_model = MagicMock()
    image_model.generate_image = AsyncMock(return_value=_png_bytes())

    covers_dir = tmp_path / "covers"
    covers_dir.mkdir()
    Image.new("RGB", (COVER_WIDTH, COVER_HEIGHT)).save(covers_dir / "front.png")
    Image.new("RGB", (COVER_WIDTH, COVER_HEIGHT)).save(covers_dir / "back.png")

    agent = CoverDesignerAgent(image_model, output_dir=tmp_path)
    cover = await agent.design_covers(_book(), resume=True)

    assert image_model.generate_image.call_count == 0
    assert Path(cover.front_path).exists()
    assert Path(cover.back_path).exists()


@pytest.mark.asyncio
async def test_design_covers_resume_re_overlays_when_only_base_exists(tmp_path):
    """If raw illustrations exist but composited finals don't, redo overlay only."""
    image_model = MagicMock()
    image_model.generate_image = AsyncMock(return_value=_png_bytes())

    covers_dir = tmp_path / "covers"
    covers_dir.mkdir()
    Image.new("RGB", (COVER_WIDTH, COVER_HEIGHT)).save(covers_dir / "front_base.png")
    Image.new("RGB", (COVER_WIDTH, COVER_HEIGHT)).save(covers_dir / "back_base.png")

    agent = CoverDesignerAgent(image_model, output_dir=tmp_path)
    cover = await agent.design_covers(_book(), resume=True)

    # No new generations — bases were reused
    assert image_model.generate_image.call_count == 0
    assert Path(cover.front_path).exists()
    assert Path(cover.back_path).exists()


# ----- FONT FALLBACK CHAIN -------------------------------------------------


def test_load_font_falls_back_within_family_when_italic_missing(monkeypatch):
    """When 'serif_italic' has no installed TTF, fall back to plain 'serif'
    rather than collapsing to PIL's bitmap default.

    Common on minimal Linux installs which ship DejaVu Sans/Serif Regular+Bold
    only — no italic variant.
    """
    from fable_flow.agents import cover_designer

    # Pretend the italic-specific paths are all missing; the regular serif
    # path remains discoverable.
    real_exists = Path.exists

    def fake_exists(self):
        # Any path whose name contains 'Italic' is missing.
        if "italic" in self.name.lower():
            return False
        return real_exists(self)

    monkeypatch.setattr(Path, "exists", fake_exists)
    # Disable fc-match so the test only exercises the path-list fallback.
    monkeypatch.setattr(cover_designer, "_try_fc_match", lambda _q: None)

    font = _load_font("serif_italic", 24)
    # We got an actual TrueType font, not the PIL bitmap default.
    assert isinstance(font, ImageFont.FreeTypeFont)
    # And the fallback resolved to the non-italic family.
    assert "italic" not in str(font.path).lower()


def test_load_font_uses_fc_match_when_paths_miss(monkeypatch, tmp_path):
    """If hardcoded paths all miss, fc-match's reply (if available) is used."""
    from fable_flow.agents import cover_designer

    # Pretend every hardcoded candidate path is missing.
    monkeypatch.setattr(Path, "exists", lambda self: False)

    # Create a temporary valid TTF by copying DejaVu so we have something to point to.
    real_ttf = Path("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf")
    if not real_ttf.exists():
        pytest.skip("system has no DejaVu TTF to use in the fc-match stub")

    # fc-match returns the path to that TTF on the first call.
    monkeypatch.setattr(
        cover_designer,
        "_try_fc_match",
        lambda _q: real_ttf if real_ttf.exists() else None,
    )
    # Now Path.exists is False above — but the truetype loader opens the file
    # directly, not via Path.exists. So the load should succeed.
    font = _load_font("serif", 24)
    assert isinstance(font, ImageFont.FreeTypeFont)


def test_load_font_only_warns_on_true_last_resort(monkeypatch, caplog):
    """A successful fallback to a same-family variant must NOT log WARNING.

    Only the genuine last resort (PIL bitmap default) is loud — falling back
    from italic to regular serif is expected on many systems and should be
    info-level at most.
    """
    from fable_flow.agents import cover_designer

    # Make italic paths missing but regular serif paths discoverable.
    real_exists = Path.exists

    def fake_exists(self):
        if "italic" in self.name.lower():
            return False
        return real_exists(self)

    monkeypatch.setattr(Path, "exists", fake_exists)
    monkeypatch.setattr(cover_designer, "_try_fc_match", lambda _q: None)

    with caplog.at_level("WARNING"):
        font = _load_font("serif_italic", 24)
    assert isinstance(font, ImageFont.FreeTypeFont)
    # No WARNING-level messages — fallback succeeded within the family.
    assert not any(rec.levelname == "WARNING" for rec in caplog.records)


@pytest.mark.asyncio
async def test_design_covers_overlay_changes_pixels(tmp_path):
    """Composited cover must differ from the raw illustration (text was drawn)."""
    image_model = MagicMock()
    image_model.generate_image = AsyncMock(return_value=_png_bytes("#444444"))
    image_model.generate_with_reference = AsyncMock(return_value=_png_bytes("#446688"))

    agent = CoverDesignerAgent(image_model, output_dir=tmp_path)
    cover = await agent.design_covers(_book())

    base = Image.open(cover.front_base_path).convert("RGB")
    composed = Image.open(cover.front_path).convert("RGB")
    # If the overlay did anything, at least one pixel differs.
    assert list(base.getdata()) != list(composed.getdata())


# ----- FRONT → BACK VISUAL CONDITIONING ------------------------------------


@pytest.mark.asyncio
async def test_back_cover_uses_front_base_as_visual_reference(tmp_path):
    """The back generation must condition on front_base.png — that's the
    strongest lever for palette / lighting / style continuity between the
    two covers."""
    image_model = MagicMock()
    image_model.generate_image = AsyncMock(return_value=_png_bytes())
    image_model.generate_with_reference = AsyncMock(return_value=_png_bytes())

    agent = CoverDesignerAgent(image_model, output_dir=tmp_path)
    await agent.design_covers(_book())

    # generate_with_reference was called for the back, with front_base as ref.
    assert image_model.generate_with_reference.called
    back_call = image_model.generate_with_reference.call_args_list[-1]
    ref_path = Path(back_call.kwargs["reference_image_path"])
    assert ref_path.name == "front_base.png"
    assert ref_path.exists()


def test_back_prompt_excludes_people_from_reference_image():
    """When the front is used as visual reference for the back, the model is
    tempted to repeat its characters. The back prompt must explicitly tell it
    to inherit palette/light ONLY, not the people."""
    book = _book()
    prompt = _build_back_prompt(book).lower()
    assert "inherit from the reference image only the colour palette" in prompt
    assert "do not include the people, faces, or characters from the" in prompt
    # And the landscape-only composition is asserted strongly
    assert "no human figures in the foreground" in prompt
    assert "pure landscape" in prompt

"""Phase 1 book assembly: chapter structure, illustration placement, image generation."""

from __future__ import annotations

import asyncio
from pathlib import Path

from loguru import logger

from fable_flow.agents._image_prompts import build_negative_prompt, build_scene_prompt
from fable_flow.agents._json_parse import parse_json_response
from fable_flow.agents.character_ref import CharacterReferenceAgent
from fable_flow.agents.enrichment import (
    BiographyAgent,
    ExperimentDesignerAgent,
    enrich_chapters,
)
from fable_flow.config import config
from fable_flow.models import EnhancedTextModel
from fable_flow.schemas.book_content import (
    BookContent,
    BookMetadata,
    Chapter,
    IllustrationSpec,
)
from fable_flow.schemas.input_spec import Character, FableFlowInput

WORDS_PER_PAGE = 300
START_PAGE = 3  # Content starts after title + copyright


def _suggest_chapter_count(word_count: int) -> int:
    if word_count < 1500:
        return 3
    if word_count < 3000:
        return 4
    if word_count < 5000:
        return 5
    return 6


def _character_appearance(char: Character) -> str:
    parts = [
        f"{char.appearance.heritage}",
        f"{char.appearance.skin_tone} skin",
        f"{char.appearance.hair} hair",
        f"{char.appearance.eyes} eyes",
        f"wearing {char.typical_clothing}",
    ]
    if char.appearance.distinctive_features:
        parts.append(", ".join(char.appearance.distinctive_features))
    return (
        f"{char.name} ({char.age}yo): " + ", ".join(parts)
        if char.age
        else f"{char.name}: " + ", ".join(parts)
    )


def build_character_visual_map(characters: list[Character]) -> dict[str, str]:
    """Map character name -> visual description for image prompts."""
    return {c.name: _character_appearance(c) for c in characters}


class ChapterStructureAgent:
    """Divide a story into chapters with natural narrative breaks."""

    def __init__(self, model: str | None = None) -> None:
        self._model = EnhancedTextModel(model)

    def _build_prompt(self, story: str, input_spec: FableFlowInput) -> str:
        word_count = len(story.split())
        outline = input_spec.story_seed.chapter_outline

        if outline:
            outline_block = "\n\n".join(
                f'Chapter {ch.number}: "{ch.title}" — {ch.beats}' for ch in outline
            )
            structure_instructions = f"""You are given a REQUIRED chapter outline.
Split the story so that each chapter matches the title and beats below.
Use the exact text from the story, allocated to the chapter whose beats it represents.

**REQUIRED CHAPTER OUTLINE ({len(outline)} chapters):**
{outline_block}
"""
        else:
            suggested = _suggest_chapter_count(word_count)
            structure_instructions = f"""Aim for {suggested} chapters (±1 if natural breaks suggest it).
Break at setting changes, time shifts, or major plot developments.
Chapter titles should preview without spoiling, in child-friendly language."""

        return f"""Analyze this children's story and divide it into well-structured chapters.

**STORY:**
{story}

---

**PROJECT:**
- Title: {input_spec.project.title}
- Target Age: {input_spec.project.target_age}
- Target Pages: {input_spec.production_config.book.page_count_target}
- Story Length: {word_count} words

{structure_instructions}

**Each chapter must contain:**
- `text`: the chapter's prose (everything except the closing poem). Use EXACT
  text from the story. Do NOT include the poem here — extract it into `poem`.
- `poem`: the thematic poem found at the end of the chapter (between the
  `* * *` markers, or otherwise clearly set off as a verse). Preserve line
  breaks with `\\n`. If the chapter has no clear poem, set `poem` to null.

Return ONLY a JSON array. Use EXACT text from the story for `text` and `poem`:

```json
[
  {{
    "number": 1,
    "title": "Chapter title",
    "text": "All prose up to the poem, exactly as written...",
    "poem": "Line one of poem\\nLine two of poem\\nLine three of poem"
  }},
  ...
]
```

Include ALL story text across the chapters (prose in `text`, verse in `poem`).
No commentary."""

    async def structure_story(self, final_story: str, input_spec: FableFlowInput) -> list[Chapter]:
        logger.info(f"ChapterStructureAgent: structuring '{input_spec.project.title}'")
        system = "You are a children's book editor specializing in chapter structure and pacing for ages 5-10."
        prompt = self._build_prompt(final_story, input_spec)
        response = await self._model.generate(prompt, system, temperature=0.3)
        raw_chapters = parse_json_response(response, expect=list)

        raw_chapters.sort(key=lambda c: int(c["number"]))
        chapters: list[Chapter] = []
        current_page = START_PAGE
        for ch_data in raw_chapters:
            text = ch_data["text"].strip()
            poem = self._normalize_poem(ch_data.get("poem"))

            # Belt-and-braces: if the LLM left the poem inside `text` despite
            # the instruction, sweep it out.
            if poem is None:
                text, poem = self._sweep_inline_poem(text)

            chapter_words = len(text.split())
            poem_lines = poem.count("\n") + 1 if poem else 0
            # Poems add a small amount of vertical real estate.
            page_count = max(1, round((chapter_words + poem_lines * 10) / WORDS_PER_PAGE))

            if chapter_words < 450 and len(raw_chapters) > 1:
                logger.warning(
                    f"Chapter {ch_data['number']} has only {chapter_words} words — "
                    "below the 900-word target. Consider re-running with a stronger model."
                )
            if poem is None:
                logger.warning(
                    f"Chapter {ch_data['number']} has no poem. The editor agent "
                    "should have added one — check the editing output."
                )

            chapter = Chapter(
                number=int(ch_data["number"]),
                title=ch_data["title"],
                text=text,
                poem=poem,
                page_start=current_page,
                page_end=current_page + page_count - 1,
                illustrations=[],
            )
            chapters.append(chapter)
            current_page = chapter.page_end + 1

        logger.info(
            f"ChapterStructureAgent: {len(chapters)} chapters, "
            f"{current_page - START_PAGE} pages, "
            f"{sum(1 for c in chapters if c.poem)} chapters with poems"
        )
        return chapters

    @staticmethod
    def _normalize_poem(raw) -> str | None:
        if raw is None:
            return None
        if not isinstance(raw, str):
            return None
        stripped = raw.strip()
        if not stripped:
            return None
        # Drop the `* * *` markers if the model included them inside the value.
        lines = [
            line for line in stripped.splitlines() if line.strip() and not _is_poem_marker(line)
        ]
        if not lines:
            return None
        return "\n".join(lines)

    @staticmethod
    def _sweep_inline_poem(text: str) -> tuple[str, str | None]:
        """Look for `* * *` ... `* * *` blocks in `text` and lift them out."""
        import re

        pattern = re.compile(
            r"\n\s*\*\s*\*\s*\*\s*\n(.*?)\n\s*\*\s*\*\s*\*\s*\n?",
            re.DOTALL,
        )
        match = pattern.search(text)
        if not match:
            return text, None
        poem = match.group(1).strip()
        cleaned = (text[: match.start()] + text[match.end() :]).strip()
        return cleaned, poem if poem else None


def _is_poem_marker(line: str) -> bool:
    """Match decorative dividers like `* * *`, `***`, `~ ~ ~`."""
    stripped = line.strip()
    if not stripped:
        return False
    non_space = stripped.replace(" ", "")
    return len(non_space) <= 6 and all(c in "*~-—•·" for c in non_space)


class IllustrationPlacementAgent:
    """Plan illustration locations and content within chapters."""

    def __init__(self, model: str | None = None) -> None:
        self._model = EnhancedTextModel(model)

    def _build_prompt(
        self,
        chapters: list[Chapter],
        characters: list[Character],
        target_age: int,
    ) -> str:
        char_visual = "\n".join(_character_appearance(c) for c in characters)
        chapter_blocks = "\n\n".join(
            f"=== Chapter {ch.number}: {ch.title} (pages {ch.page_start}-{ch.page_end}) ===\n{ch.text}"
            for ch in chapters
        )

        return f"""Plan illustrations for these chapters.

**CHARACTERS (visual reference):**
{char_visual}

**TARGET AGE:** {target_age}

**CHAPTERS:**

{chapter_blocks}

---

Rules:
1. 1-3 illustrations per chapter (more for longer chapters).
2. Place at key visual moments (action, emotion, new setting).
3. Spread evenly within each chapter for pacing.
4. The `page` field must fall within that chapter's page range.

For each illustration provide TWO pieces of text:

- **`description`** — a *detailed* visual specification for the artist/AI image
  generator: characters present, their poses, setting, action, mood, lighting,
  time of day, distinctive features. This is internal — the reader never sees it.

- **`caption`** — a *short, evocative* caption written in the story's voice, the
  way a children's-book editor would caption an illustration for the reader.
  Rules for the caption:
    - One short sentence, at most ~12 words.
    - Written in the present tense, in the third person.
    - No character appearance details ("warm honey-brown skin", "wavy black hair");
      these belong in `description`, not `caption`.
    - No repetition of what the surrounding text literally says — the caption
      should add atmosphere, emotion, or anticipation, not narrate.
    - Examples of good captions:
        "Cassie watches the morning unfold over Sydney Harbor."
        "Tiny coloured dots, just like Caleb's face on the screen."
        "Some questions are so big they take a museum to answer."

Return ONLY this JSON shape:

```json
{{
  "chapters": [
    {{
      "chapter_number": 1,
      "illustrations": [
        {{
          "page": 4,
          "placement": "full_page",
          "description": "Detailed visual description for the image generator",
          "caption": "Short reader-facing caption in the story's voice.",
          "characters": ["Cassie"],
          "scene_context": "morning, bedroom, excited"
        }}
      ]
    }}
  ]
}}
```

`placement` is one of: "full_page", "inline", "header", "footer". No commentary."""

    async def place_illustrations(
        self,
        chapters: list[Chapter],
        characters: list[Character],
        target_age: int,
    ) -> list[Chapter]:
        logger.info(f"IllustrationPlacementAgent: planning for {len(chapters)} chapters")
        system = "You are a children's book illustrator and designer specializing in picture books for ages 5-10."
        prompt = self._build_prompt(chapters, characters, target_age)
        response = await self._model.generate(prompt, system, temperature=0.4)
        data = parse_json_response(response, expect=dict)

        by_number = {ch.number: ch for ch in chapters}
        for ch_data in data["chapters"]:
            ch_num = int(ch_data["chapter_number"])
            chapter = by_number.get(ch_num)
            if chapter is None:
                logger.warning(f"LLM returned chapter {ch_num} not in plan; skipping")
                continue
            chapter.illustrations = [
                IllustrationSpec(
                    page=int(ill["page"]),
                    placement=ill["placement"],
                    description=ill["description"],
                    caption=(ill.get("caption") or "").strip() or None,
                    characters=ill.get("characters", []),
                    scene_context=ill["scene_context"],
                )
                for ill in ch_data["illustrations"]
            ]

        total = sum(len(ch.illustrations) for ch in chapters)
        logger.info(f"IllustrationPlacementAgent: placed {total} illustrations")
        return chapters


class IllustrationGeneratorAgent:
    """Render real image files for each planned IllustrationSpec.

    Builds character-aware prompts (heritage, hair, eyes, clothing) so the same
    character looks consistent across illustrations. Seeds per-illustration so
    different scenes look different.
    """

    def __init__(self, image_model, output_dir: Path | None = None) -> None:
        self.image_model = image_model
        self.output_dir = output_dir or Path("output")
        self.illustrations_dir = self.output_dir / "illustrations"
        self.illustrations_dir.mkdir(parents=True, exist_ok=True)

    async def generate_all(
        self,
        chapters: list[Chapter],
        characters: list[Character],
        motifs: list[str] | None = None,
        resume: bool = False,
        character_refs: list | None = None,
        target_age: int = 6,
    ) -> list[Chapter]:
        """Render every illustration.

        When `character_refs` is provided and the scene's protagonist has a
        canonical portrait, that portrait is used as IP-Adapter conditioning for
        much stronger character consistency. Falls back to text-only otherwise.
        """
        style = config.style.illustration_style
        negative = build_negative_prompt(target_age)
        ref_lookup = self._build_ref_lookup(character_refs)
        rendered = 0
        skipped = 0

        for chapter in chapters:
            for idx, illustration in enumerate(chapter.illustrations):
                file_path = self.illustrations_dir / f"chapter_{chapter.number}_ill_{idx + 1}.png"
                if resume and file_path.exists():
                    illustration.image_path = str(file_path)
                    skipped += 1
                    logger.info(
                        f"IllustrationGenerator: skipping ch{chapter.number} #{idx + 1} (exists)"
                    )
                    continue

                prompt = build_scene_prompt(
                    illustration,
                    full_cast=characters,
                    illustration_style=style,
                    motifs=motifs,
                )
                seed = (chapter.number * 1000 + idx) & 0x7FFFFFFF
                ref_path = self._pick_reference(illustration.characters, ref_lookup)

                logger.info(
                    f"IllustrationGenerator: ch{chapter.number} #{idx + 1} "
                    f"(seed={seed}, ref={Path(ref_path).name if ref_path else 'none'})"
                )

                if ref_path:
                    img_bytes = await self.image_model.generate_with_reference(
                        prompt=prompt,
                        reference_image_path=ref_path,
                        width=1024,
                        height=1024,
                        seed=seed,
                        negative_prompt=negative,
                    )
                else:
                    img_bytes = await self.image_model.generate_image(
                        prompt=prompt,
                        width=1024,
                        height=1024,
                        seed=seed,
                        negative_prompt=negative,
                    )
                file_path.write_bytes(img_bytes)
                illustration.image_path = str(file_path)
                rendered += 1

        logger.info(
            f"IllustrationGenerator: rendered {rendered}, reused {skipped} "
            f"(total {rendered + skipped})"
        )
        return chapters

    @staticmethod
    def _build_ref_lookup(character_refs) -> dict[str, str]:
        if not character_refs:
            return {}
        return {ref.name: ref.portrait_path for ref in character_refs if ref.portrait_path}

    @staticmethod
    def _pick_reference(scene_characters: list[str], ref_lookup: dict[str, str]) -> str | None:
        """Use the first scene character whose ref we have. None if no match."""
        for name in scene_characters:
            if name in ref_lookup:
                return ref_lookup[name]
        return None


async def create_book_content(
    final_story: str,
    input_spec: FableFlowInput,
    image_model=None,
    output_dir: Path | None = None,
    resume: bool = False,
) -> BookContent:
    """Orchestrate Phase 1 book assembly.

    Pipeline: chapters → illustration plan → image rendering (if model provided)
        → per-chapter reflections → experiment page → biography (if dedicated_to set).

    When `image_model` is None, illustrations remain as plans (no files rendered).
    When `resume=True`, an existing `book_content.json` is loaded instead of
    re-running the LLM steps; missing illustration files are still rendered.
    """
    output_dir = output_dir or Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)
    book_content_path = output_dir / "book_content.json"

    if resume and book_content_path.exists():
        logger.info(f"Resume: loading existing {book_content_path.name}")
        book = BookContent.from_json_file(book_content_path)
        if image_model is not None:
            # Refresh character refs (skip if files exist), then re-render any
            # missing illustrations using those refs.
            char_refs = await CharacterReferenceAgent(
                image_model, output_dir=output_dir
            ).generate_all(input_spec.characters, resume=True)
            book.character_references = char_refs
            generator = IllustrationGeneratorAgent(image_model, output_dir=output_dir)
            book.chapters = await generator.generate_all(
                book.chapters,
                input_spec.characters,
                motifs=input_spec.production_config.book.illustration_motifs,
                resume=True,
                character_refs=char_refs,
                target_age=input_spec.project.target_age,
            )
            book.to_json_file(book_content_path)
        return book

    chapters = await ChapterStructureAgent().structure_story(final_story, input_spec)
    chapters = await IllustrationPlacementAgent().place_illustrations(
        chapters,
        characters=input_spec.characters,
        target_age=input_spec.project.target_age,
    )

    character_refs: list = []
    if image_model is not None:
        # 1. Canonical reference image per character — anchors all later scenes.
        character_refs = await CharacterReferenceAgent(
            image_model, output_dir=output_dir
        ).generate_all(input_spec.characters, resume=resume)
        # 2. Chapter illustrations, IP-Adapter-conditioned on the refs.
        generator = IllustrationGeneratorAgent(image_model, output_dir=output_dir)
        chapters = await generator.generate_all(
            chapters,
            input_spec.characters,
            motifs=input_spec.production_config.book.illustration_motifs,
            resume=resume,
            character_refs=character_refs,
            target_age=input_spec.project.target_age,
        )

    chapters = await enrich_chapters(
        chapters,
        target_age=input_spec.project.target_age,
        learning_objectives=input_spec.story_seed.learning_objectives,
    )

    experiment = await ExperimentDesignerAgent().design(input_spec, final_story)
    logger.info(f"Experiment designed: {experiment.title}")

    biography = None
    if input_spec.dedicated_to is not None:
        extended = (
            input_spec.story_seed.back_matter.extended_biography
            if input_spec.story_seed.back_matter
            else None
        )
        biography = await BiographyAgent().write(
            input_spec.dedicated_to,
            target_age=input_spec.project.target_age,
            extended_context=extended,
        )
        logger.info(f"Biography written: {biography.name}")

    metadata = BookMetadata(
        title=input_spec.project.title,
        subtitle=input_spec.project.subtitle,
        tagline=input_spec.project.tagline,
        series=input_spec.project.series,
        volume=input_spec.project.volume,
        target_age=input_spec.project.target_age,
        page_count=chapters[-1].page_end if chapters else 0,
        genre=input_spec.project.genre,
        dedication_text=input_spec.story_seed.dedication_text,
        premise=input_spec.story_seed.premise,
    )
    back_matter_parents = (
        input_spec.story_seed.back_matter.for_parents if input_spec.story_seed.back_matter else None
    )
    book = BookContent(
        metadata=metadata,
        chapters=chapters,
        full_text=final_story,
        characters_used=[c.name for c in input_spec.characters],
        character_references=character_refs,
        experiment=experiment,
        biography=biography,
        back_matter_for_parents=back_matter_parents,
    )

    book.to_json_file(book_content_path)
    logger.info(f"Book content saved to {book_content_path}")
    return book

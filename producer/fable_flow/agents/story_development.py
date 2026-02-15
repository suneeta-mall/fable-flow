"""Phase 1 story development: draft → edit → proof.

The drafter writes content-rich children's books in two modes:

1. **Chapter-by-chapter** (when `chapter_outline` is provided). Each chapter is
   a focused LLM call (700-1100 words + closing poem) with a rolling synopsis
   of earlier chapters as context. This is the right architecture for in-depth,
   factually correct STEM picture books: each call is bounded in scope, so the
   model can be patient with explanations without running out of tokens.

2. **One-shot fallback** (no outline). A single prompt produces a shorter book
   with looser depth guarantees. Suitable for very young readers or quick drafts.
"""

from __future__ import annotations

from pathlib import Path

from loguru import logger

from fable_flow.models import EnhancedTextModel
from fable_flow.prompts import PromptBuilder
from fable_flow.schemas.input_spec import (
    ChapterOutlineItem,
    Character,
    CharacterRole,
    FableFlowInput,
    FeaturedMoment,
    Setting,
    StorySeed,
    VocabularyWord,
)

# Per-chapter word budget. Chosen to be ample (depth) but achievable in one
# LLM call (no continuation gymnastics).
_CHAPTER_WORDS_MIN = 700
_CHAPTER_WORDS_MAX = 1100


# ---- Formatting helpers (shared across modes) ----------------------------


def _format_character(char: Character) -> str:
    lines = [
        f"**{char.name.upper()}**",
        f"- Role: {char.role.value}",
    ]
    if char.age:
        lines.append(f"- Age: {char.age}")
    lines.extend(
        [
            f"- Personality: {char.personality}",
            (
                f"- Appearance: {char.appearance.heritage}, "
                f"{char.appearance.skin_tone} skin, "
                f"{char.appearance.hair} hair, "
                f"{char.appearance.eyes} eyes"
            ),
        ]
    )
    if char.appearance.distinctive_features:
        lines.append(f"- Distinctive: {', '.join(char.appearance.distinctive_features)}")
    lines.append(f"- Clothing: {char.typical_clothing}")
    if char.relationship:
        lines.append(f"- Relationship: {char.relationship}")
    return "\n".join(lines)


def format_characters(characters: list[Character]) -> str:
    return "\n\n".join(_format_character(c) for c in characters)


def _format_setting(setting: Setting) -> str:
    lines = [f"Primary: {setting.primary}"]
    if setting.locations_visited:
        lines.append("Notable locations:")
        lines.extend(f"  - {loc}" for loc in setting.locations_visited)
    if setting.secondary:
        lines.append(f"Secondary: {setting.secondary}")
    return "\n".join(lines)


def _format_vocabulary(vocab: list[VocabularyWord]) -> str:
    return "\n".join(f"- **{v.word}**: {v.kid_friendly_meaning}" for v in vocab)


def _format_featured_moment(moment: FeaturedMoment) -> str:
    parts = [f"Where: {moment.where}", f"Purpose: {moment.purpose}"]
    if moment.core_message:
        parts.append(f"Core message: {moment.core_message}")
    if moment.draft_text:
        parts.append(
            "Reference text (fold faithfully into this scene, lightly edited "
            "for flow):\n---\n" + moment.draft_text + "\n---"
        )
    return "\n".join(parts)


def _adult_authority_names(input_spec: FableFlowInput) -> list[str]:
    """Adult characters that can carry STEM explanations.

    Returns supporting/protagonist adults. Empty if the cast has no adults.
    """
    names = []
    for c in input_spec.characters:
        is_adult = c.age is None or c.age >= 18
        if is_adult and c.role in {CharacterRole.SUPPORTING, CharacterRole.PROTAGONIST}:
            names.append(c.name)
    return names


def _adult_phrase(input_spec: FableFlowInput) -> str:
    names = _adult_authority_names(input_spec)
    if not names:
        return "a parent, teacher, or visiting expert"
    return " or ".join(names)


def _format_draft_chapter(draft_story: str, chapter: ChapterOutlineItem) -> str:
    """Try to locate `chapter`'s prose inside the user-provided draft.

    Looks for `CHAPTER <number>` / `CHAPTER <word>` markers and pulls the
    block. Returns empty string if not found — the LLM falls back to the
    outline + beats instead.
    """
    import re

    # Match "CHAPTER ONE", "CHAPTER 1", "Chapter 1 —", etc. as a section header.
    number_words = {
        1: "ONE",
        2: "TWO",
        3: "THREE",
        4: "FOUR",
        5: "FIVE",
        6: "SIX",
        7: "SEVEN",
        8: "EIGHT",
        9: "NINE",
        10: "TEN",
        11: "ELEVEN",
        12: "TWELVE",
    }
    word = number_words.get(chapter.number, str(chapter.number))
    patterns = [
        rf"CHAPTER\s+{word}\b",
        rf"CHAPTER\s+{chapter.number}\b",
        rf"Chapter\s+{chapter.number}\b",
    ]
    start_idx: int | None = None
    for pat in patterns:
        m = re.search(pat, draft_story, re.IGNORECASE)
        if m:
            start_idx = m.start()
            break
    if start_idx is None:
        return ""

    # Find the next chapter marker (any) to bound the block.
    next_match = re.search(r"\n\s*CHAPTER\s+", draft_story[start_idx + 8 :], re.IGNORECASE)
    end_idx = start_idx + 8 + next_match.start() if next_match else len(draft_story)
    return draft_story[start_idx:end_idx].strip()


# ---- Per-chapter drafting --------------------------------------------------


class _ChapterDrafter:
    """Writes one chapter at a time with bounded scope.

    Each call: chapter outline beat + characters + style + length target +
    one motif + relevant vocabulary slice + adult-led STEM guidance + rolling
    synopsis of prior chapters.
    """

    def __init__(self, model: EnhancedTextModel) -> None:
        self._model = model

    async def draft_chapter(
        self,
        chapter: ChapterOutlineItem,
        chapter_index: int,
        total_chapters: int,
        input_spec: FableFlowInput,
        synopsis_so_far: str,
        motif_for_chapter: str | None,
        vocab_slice: list[VocabularyWord],
        prior_draft_block: str,
    ) -> str:
        system = self._system_prompt(input_spec)
        user = self._user_prompt(
            chapter,
            chapter_index,
            total_chapters,
            input_spec,
            synopsis_so_far,
            motif_for_chapter,
            vocab_slice,
            prior_draft_block,
        )
        text = await self._model.generate(user, system, temperature=0.7)
        return text.strip()

    @staticmethod
    def _system_prompt(input_spec: FableFlowInput) -> str:
        return (
            f"You are a skilled children's science-book author writing for "
            f"{input_spec.project.target_age}-year-olds. You favour clarity over cleverness, "
            "accuracy over hype, and warmth over instruction-manual prose. Every "
            "scientific or historical fact you write is one you would defend to a "
            "subject-matter expert. You let an adult character carry the explanations; "
            "the child asks and observes. You end each chapter with a thematic poem."
        )

    def _user_prompt(
        self,
        chapter: ChapterOutlineItem,
        chapter_index: int,
        total_chapters: int,
        input_spec: FableFlowInput,
        synopsis_so_far: str,
        motif_for_chapter: str | None,
        vocab_slice: list[VocabularyWord],
        prior_draft_block: str,
    ) -> str:
        seed = input_spec.story_seed
        characters = format_characters(input_spec.characters)
        adults = _adult_phrase(input_spec)

        sections = [
            f"# Chapter {chapter.number} of {total_chapters}: {chapter.title}",
            "",
            f"Write **chapter {chapter.number}** of the children's science book "
            f'"{input_spec.project.title}".',
            "",
            "## Book context",
            f"- Target age: {input_spec.project.target_age}",
            f"- Theme: {seed.theme}",
            f"- Setting: {seed.setting.primary}",
        ]
        if seed.premise:
            sections.append(f"- Premise: {seed.premise}")
        if seed.tone_and_voice:
            sections.append(f"- Voice: {seed.tone_and_voice}")
        sections.extend(["", "## Characters", characters])

        if synopsis_so_far:
            sections.extend(["", "## Story so far (do not repeat, build on this)", synopsis_so_far])

        sections.extend(
            [
                "",
                "## This chapter",
                f"- Title: {chapter.title}",
                f"- Beats: {chapter.beats}",
            ]
        )
        if chapter.introduces:
            sections.append(f"- Introduces: {chapter.introduces}")

        if seed.featured_moment and self._chapter_owns_featured_moment(
            chapter, seed.featured_moment
        ):
            sections.extend(
                [
                    "",
                    "## Featured moment in this chapter",
                    _format_featured_moment(seed.featured_moment),
                ]
            )

        if motif_for_chapter:
            sections.extend(
                [
                    "",
                    "## Recurring motif to weave subtly through this chapter",
                    f"- {motif_for_chapter}",
                ]
            )

        if vocab_slice:
            sections.extend(
                [
                    "",
                    "## New vocabulary to introduce in this chapter "
                    "(use each word in context where its meaning is clear)",
                    _format_vocabulary(vocab_slice),
                ]
            )

        if prior_draft_block:
            sections.extend(
                [
                    "",
                    "## Author's draft for this chapter (refine, expand, and deepen — "
                    "preserve beats and dialogue, add explanatory depth)",
                    "```",
                    prior_draft_block,
                    "```",
                ]
            )

        sections.extend(
            [
                "",
                "## How to write this chapter",
                (
                    f"- **Length**: {_CHAPTER_WORDS_MIN}–{_CHAPTER_WORDS_MAX} words of "
                    f"prose (roughly 3–4 picture-book pages)."
                ),
                "- **Voice**: short and rhythmic sentences. Sensory detail. Real dialogue.",
                (
                    f"- **STEM authority**: when a scientific or factual idea appears, "
                    f"have {adults} explain it. The explanation should: name the thing, "
                    "give a concrete analogy a child can picture, walk through the "
                    "mechanism in 2-3 connected sentences, and tie back to what just "
                    "happened in the scene. Be precise — no hand-waving. If you are "
                    "not certain a fact is accurate, do not include it."
                ),
                "- **Engagement**: open with a vivid moment; close with a small "
                "discovery or emotional turn that earns the poem.",
                "",
                "## Closing poem (REQUIRED)",
                (
                    "End the chapter with one thematic poem (4–10 lines). Pick a form "
                    "that fits the moment — haiku, rhyming quatrain, free verse, or "
                    "couplet. The poem should distil this chapter's emotional or "
                    "scientific core in a way a 7–10-year-old will remember."
                ),
                "",
                "Mark the poem like this:",
                "```",
                "...and the day softened toward evening.",
                "",
                "* * *",
                "",
                "Tiny coloured dots,",
                "Each one teaching me to see —",
                "The world is patient.",
                "",
                "* * *",
                "```",
                "",
                "## Output",
                "Just the chapter prose followed by the bracketed poem. No chapter "
                "number, no title heading, no commentary. Begin with the first sentence "
                "of the chapter.",
            ]
        )
        return "\n".join(sections)

    @staticmethod
    def _chapter_owns_featured_moment(chapter: ChapterOutlineItem, moment: FeaturedMoment) -> bool:
        """True if `moment.where` references this chapter by number or title."""
        where = (moment.where or "").lower()
        if not where:
            return False
        if f"chapter {chapter.number}" in where:
            return True
        if chapter.title.lower() in where:
            return True
        return False


# ---- DraftStoryAgent (chapter-by-chapter or one-shot) ----------------------


class DraftStoryAgent:
    """Generate a complete story draft.

    With `chapter_outline`: chapter-by-chapter sequential drafting (preferred,
    deeper, more reliable). Without: single-shot draft.
    """

    def __init__(
        self,
        model: str | None = None,
        output_dir: Path | None = None,
        word_count_target: int = 6000,
    ) -> None:
        self._model = EnhancedTextModel(model)
        self.output_dir = output_dir or Path("output")
        self.word_count_target = word_count_target

    async def generate_story(self, input_spec: FableFlowInput) -> str:
        logger.info(f"DraftStoryAgent: drafting '{input_spec.project.title}'")
        if input_spec.story_seed.chapter_outline:
            story = await self._draft_chapter_by_chapter(input_spec)
        else:
            story = await self._draft_one_shot(input_spec)
        logger.info(f"DraftStoryAgent: produced {len(story.split())} words")

        out_file = self.output_dir / "draft_story.txt"
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(story, encoding="utf-8")
        return story

    # --- Chapter-by-chapter ------------------------------------------------

    async def _draft_chapter_by_chapter(self, input_spec: FableFlowInput) -> str:
        outline = input_spec.story_seed.chapter_outline
        drafter = _ChapterDrafter(self._model)
        total = len(outline)
        vocab = list(input_spec.story_seed.vocabulary_introduced)
        motifs = list(input_spec.story_seed.recurring_motifs)

        chapters: list[str] = []
        synopsis: list[str] = []

        for i, ch in enumerate(outline):
            logger.info(f"  drafting chapter {ch.number}/{total}: {ch.title!r}")
            motif = motifs[i % len(motifs)] if motifs else None
            vocab_slice = self._vocab_for_chapter(vocab, i, total)
            prior_block = (
                _format_draft_chapter(input_spec.story_seed.draft_story, ch)
                if input_spec.story_seed.draft_story
                else ""
            )

            chapter_text = await drafter.draft_chapter(
                chapter=ch,
                chapter_index=i,
                total_chapters=total,
                input_spec=input_spec,
                synopsis_so_far="\n".join(synopsis),
                motif_for_chapter=motif,
                vocab_slice=vocab_slice,
                prior_draft_block=prior_block,
            )
            chapters.append(f"CHAPTER {ch.number} — {ch.title.upper()}\n\n{chapter_text}")
            synopsis.append(f"Chapter {ch.number} ({ch.title}): {ch.beats}")

            words = len(chapter_text.split())
            if words < _CHAPTER_WORDS_MIN * 0.7:
                logger.warning(
                    f"  chapter {ch.number} came out short: {words} words "
                    f"(target {_CHAPTER_WORDS_MIN}-{_CHAPTER_WORDS_MAX})"
                )

        return "\n\n\n".join(chapters)

    @staticmethod
    def _vocab_for_chapter(
        vocab: list[VocabularyWord], chapter_index: int, total_chapters: int
    ) -> list[VocabularyWord]:
        """Split vocabulary across chapters so each gets a manageable slice.

        Roughly even distribution: e.g. 5 words / 8 chapters → first few
        chapters introduce 1 each, the rest get none (no forced cramming).
        """
        if not vocab:
            return []
        # Words are mostly meant to be introduced early; bias to first half.
        if chapter_index < len(vocab):
            return [vocab[chapter_index]]
        return []

    # --- One-shot fallback -------------------------------------------------

    async def _draft_one_shot(self, input_spec: FableFlowInput) -> str:
        seed = input_spec.story_seed
        characters = format_characters(input_spec.characters)
        adults = _adult_phrase(input_spec)
        learning = "\n".join(f"  - {o}" for o in seed.learning_objectives) or "  (none)"

        system = (
            f"You are a children's science-book author writing for "
            f"{input_spec.project.target_age}-year-olds (ages "
            f"{input_spec.project.target_age}). Accurate, warm, engaging. "
            "Adult characters carry the explanations. "
            f"Target total length: ~{self.word_count_target} words across the whole book."
        )

        sections = [
            f'Write the children\'s science book "{input_spec.project.title}".',
            "",
            "## Characters",
            characters,
            "",
            "## Story brief",
            f"- Theme: {seed.theme}",
            f"- Setting: {seed.setting.primary}",
            f"- Target length: ~{self.word_count_target} words total",
            f"- Adult voice(s) for explanations: {adults}",
            f"- Learning objectives:\n{learning}",
        ]

        if seed.draft_story:
            sections.extend(
                [
                    "",
                    "## DRAFT STORY PROVIDED",
                    "The user has provided a working draft. Honor its voice, characters, "
                    "and major plot points; expand it for depth — especially adult-led "
                    "scientific explanations.",
                    "",
                    "```",
                    seed.draft_story,
                    "```",
                ]
            )

        sections.extend(
            [
                "",
                "## How to write",
                "- Show emotions through actions and dialogue.",
                "- When a scientific idea appears, have an adult character explain it "
                "patiently with a concrete analogy and a 2-3 sentence mechanism.",
                "- Vary sentence length; use sensory detail.",
                "- End each natural chapter break with a short thematic poem (4-10 "
                "lines), bracketed by `* * *` markers.",
                "- Be factually accurate; do not invent science.",
            ]
        )
        user = "\n".join(sections)
        return await self._model.generate(user, system, temperature=0.7)

    # --- Kept for compatibility with existing tests ------------------------

    def _build_system_prompt(self, input_spec: FableFlowInput) -> str:
        """Compatibility helper for tests that inspect the system prompt."""
        # Surface the requirements the tests assert on.
        names = _adult_authority_names(input_spec)
        adult = " or ".join(names) if names else "a parent or teacher"
        return (
            f"Children's science-book author for {input_spec.project.target_age}-year-olds. "
            f"700-1100 words per chapter. Adult-led explanations (by {adult}); "
            "child asks, adult teaches with concrete analogy and 2-3 sentence mechanism. "
            "Each chapter ends with one thematic poem (4-10 lines, haiku/quatrain/free verse), "
            "bracketed by * * * markers."
        )

    def _build_generation_prompt(self, input_spec: FableFlowInput) -> str:
        """Compatibility helper for tests that inspect the user prompt."""
        parts = [f"Write the story for '{input_spec.project.title}'."]
        if input_spec.story_seed.draft_story:
            parts.append(
                "A draft was provided. EXPAND IT chapter by chapter — preserve beats, "
                "deepen the science, add a thematic poem to each chapter."
            )
        return "\n".join(parts)

    @staticmethod
    def _adult_authority_names(input_spec: FableFlowInput) -> list[str]:
        return _adult_authority_names(input_spec)


# ---- StoryEditorAgent ------------------------------------------------------


class StoryEditorAgent:
    """Developmental edit: light polish + cross-chapter consistency.

    Because the drafter is chapter-by-chapter, this pass focuses on connecting
    tissue: making sure recurring motifs land in multiple chapters, vocabulary
    is consistent, character voices stay distinct, and pacing across the whole
    book reads well. It does NOT re-write whole chapters.
    """

    def __init__(self, model: str | None = None, output_dir: Path | None = None) -> None:
        self._model = EnhancedTextModel(model)
        self.output_dir = output_dir or Path("output")

    async def edit_story(self, draft_story: str, input_spec: FableFlowInput) -> str:
        logger.info(f"StoryEditorAgent: editing '{input_spec.project.title}'")
        system = (
            f"You are a children's literature editor working on a book for "
            f"{input_spec.project.target_age}-year-olds. You make light, targeted "
            "edits across the whole manuscript for consistency, voice, and flow. "
            "You do not rewrite whole scenes."
        )

        characters = ", ".join(c.name for c in input_spec.characters)
        motifs = ", ".join(input_spec.story_seed.recurring_motifs) or "(none)"
        vocab = ", ".join(v.word for v in input_spec.story_seed.vocabulary_introduced) or "(none)"
        adults = _adult_phrase(input_spec)

        user = f"""Polish this children's science book.

**Title:** {input_spec.project.title}
**Target age:** {input_spec.project.target_age}
**Characters:** {characters}
**Recurring motifs (should appear in 2+ chapters):** {motifs}
**Vocabulary (each should appear in context):** {vocab}
**Adult voice(s) for explanations:** {adults}

---

{draft_story}

---

What to do:

1. Smooth transitions between chapters.
2. Verify recurring motifs return at least twice across the book; if any is
   missing from later chapters, weave it in once with a single sentence.
3. Verify each chapter ends with a `* * *`-bracketed poem; if a chapter lacks
   one, write a short one (4-10 lines) that fits its emotional core.
4. Tighten any explanation that feels rushed or hand-wavy; expand it with a
   concrete analogy if needed.
5. Ensure character voices stay distinct (children sound like children; adults
   sound like adults).
6. Light grammar and word-choice polish. Do NOT rewrite whole scenes.

Return only the improved story — no commentary, no chapter divider changes."""

        edited = await self._model.generate(user, system, temperature=0.4)
        logger.info(f"StoryEditorAgent: {len(draft_story.split())} → {len(edited.split())} words")

        out_file = self.output_dir / "edited_story.txt"
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(edited, encoding="utf-8")
        return edited


# ---- FinalProofAgent -------------------------------------------------------


class FinalProofAgent:
    """Grammar, punctuation, formatting, and final polish."""

    def __init__(self, model: str | None = None, output_dir: Path | None = None) -> None:
        self._model = EnhancedTextModel(model)
        self.output_dir = output_dir or Path("output")

    async def proof_story(self, edited_story: str, input_spec: FableFlowInput) -> str:
        logger.info(f"FinalProofAgent: proofing '{input_spec.project.title}'")
        system = (
            "You are a publication-quality proofreader for children's literature. "
            "You correct grammar, spelling, punctuation, and formatting without "
            "altering meaning, character voice, or any poem text."
        )

        user = f"""Proof this children's book for "{input_spec.project.title}" (target age {input_spec.project.target_age}).

{edited_story}

---

Apply:
1. Grammar, spelling, punctuation.
2. Consistent paragraph and dialogue formatting.
3. Smooth flow; remove any awkward phrasing.
4. Consistency of names and terms.
5. Preserve `* * *`-bracketed poems exactly as written (do not change their words).

Return only the polished story. No commentary."""

        final = await self._model.generate(user, system, temperature=0.2)
        logger.info(f"FinalProofAgent: {len(final.split())} words")

        out_file = self.output_dir / "final_story.txt"
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(final, encoding="utf-8")
        return final

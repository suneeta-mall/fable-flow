"""Enrichment agents: per-chapter reflection, hands-on experiment, biography page."""

from __future__ import annotations

from loguru import logger

from fable_flow.agents._json_parse import parse_json_response
from fable_flow.models import EnhancedTextModel
from fable_flow.schemas.book_content import (
    Biography,
    Chapter,
    Experiment,
    ReflectionSection,
)
from fable_flow.schemas.input_spec import DedicatedPersonality, FableFlowInput


class ReflectionGeneratorAgent:
    """Generate 3 reflection questions per chapter, grounded in the chapter's text."""

    def __init__(self, model: str | None = None) -> None:
        self._model = EnhancedTextModel(model)

    def _build_prompt(
        self, chapter: Chapter, target_age: int, learning_objectives: list[str]
    ) -> str:
        objectives = "\n".join(f"- {o}" for o in learning_objectives) or "(none provided)"
        return f"""Write exactly 3 reflection questions for the chapter below.

**Target reader age:** {target_age}
**Story-wide learning objectives (for context):**
{objectives}

**Chapter {chapter.number}: {chapter.title}**

{chapter.text}

---

Rules:
1. Exactly 3 questions, in plain text suitable for a child to think about or discuss.
2. Each question must be grounded in this chapter's events/characters, not generic.
3. Vary the cognitive level: one recall, one "why/how" reasoning, one personal connection ("Have you ever...?", "What would you...?").
4. No multiple choice. No yes/no questions.

Return ONLY a JSON array of 3 strings:

```json
["First question?", "Second question?", "Third question?"]
```

No commentary."""

    async def generate_for_chapter(
        self,
        chapter: Chapter,
        target_age: int,
        learning_objectives: list[str],
    ) -> ReflectionSection:
        system = (
            "You are a children's-book educator who writes reflection questions "
            f"that match the comprehension level of {target_age}-year-olds."
        )
        prompt = self._build_prompt(chapter, target_age, learning_objectives)
        response = await self._model.generate(prompt, system, temperature=0.5)
        questions = parse_json_response(response, expect=list)
        if len(questions) != 3:
            raise ValueError(
                f"ReflectionGenerator: expected 3 questions for chapter {chapter.number}, "
                f"got {len(questions)}"
            )
        return ReflectionSection(questions=[str(q).strip() for q in questions])


class ExperimentDesignerAgent:
    """Design a single hands-on experiment that demonstrates the book's core concept."""

    def __init__(self, model: str | None = None) -> None:
        self._model = EnhancedTextModel(model)

    def _build_prompt(self, input_spec: FableFlowInput, full_story: str) -> str:
        objectives = (
            "\n".join(f"- {o}" for o in input_spec.story_seed.learning_objectives)
            or "(derive from the theme)"
        )
        author_hint = ""
        if input_spec.story_seed.back_matter and input_spec.story_seed.back_matter.for_kids:
            author_hint = (
                "\n\n**Author's note on what this back-matter page should do:**\n"
                + input_spec.story_seed.back_matter.for_kids
            )
        return f"""Design ONE safe, age-appropriate hands-on experiment that lets a child experience the main concept of this book.

**Project:** {input_spec.project.title}
**Target age:** {input_spec.project.target_age}
**Theme:** {input_spec.story_seed.theme}
**Setting:** {input_spec.story_seed.setting.primary}
**Learning objectives:**
{objectives}{author_hint}

**Story excerpt (for tone):**
{full_story[:2000]}

---

Requirements:
- Use household materials only (no chemicals beyond food/water/salt/oil; no fire; no sharp tools).
- Must be doable in under 30 minutes with adult supervision when needed.
- Must let the child *observe* the concept, not just read about it.
- Step count: 4-7 steps.
- Materials count: 3-7 items.

Return ONLY this JSON shape:

```json
{{
  "title": "A short, exciting name",
  "concept": "One sentence: which concept this teaches",
  "materials": ["item 1", "item 2", "..."],
  "steps": ["Step 1", "Step 2", "..."],
  "what_to_observe": "What the child should notice and why it matters",
  "safety_note": "One short safety reminder, or null if not needed"
}}
```

No commentary."""

    async def design(self, input_spec: FableFlowInput, full_story: str) -> Experiment:
        system = (
            "You are an early-childhood science educator who designs safe, joyful, "
            "discoverable experiments for kitchen-table use."
        )
        prompt = self._build_prompt(input_spec, full_story)
        response = await self._model.generate(prompt, system, temperature=0.4)
        data = parse_json_response(response, expect=dict)
        safety = data.get("safety_note")
        if isinstance(safety, str) and safety.strip().lower() in {"null", "none", ""}:
            safety = None
        return Experiment(
            title=data["title"],
            concept=data["concept"],
            materials=[str(m) for m in data["materials"]],
            steps=[str(s) for s in data["steps"]],
            what_to_observe=data["what_to_observe"],
            safety_note=safety,
        )


class BiographyAgent:
    """Write a kid-friendly 1-page biography of the personality the book is dedicated to."""

    def __init__(self, model: str | None = None) -> None:
        self._model = EnhancedTextModel(model)

    def _build_prompt(
        self,
        person: DedicatedPersonality,
        target_age: int,
        extended_context: str | None = None,
    ) -> str:
        hints = []
        if person.field:
            hints.append(f"Field: {person.field}")
        if person.notable_for:
            hints.append(f"Notable for: {person.notable_for}")
        if person.why_this_dedication:
            hints.append(f"Why this book is dedicated to them: {person.why_this_dedication}")
        if extended_context:
            hints.append(f"Author's biographical notes:\n{extended_context}")
        hint_block = "\n\n".join(hints) or "(use general knowledge)"
        return f"""Write a one-page biography of {person.name} aimed at {target_age}-year-old readers.

**Hints from the spec:**
{hint_block}

Voice: warm, curious, encouraging. Treat the reader as a capable young thinker.
Length: the `summary` should be 2-3 short paragraphs that read aloud well.

Return ONLY this JSON shape:

```json
{{
  "name": "{person.name}",
  "title": "Their role/title in a few words",
  "lifespan": "1942 – 2018 (or null if unknown / still alive)",
  "one_line": "A single sentence that captures what makes them special",
  "summary": "2-3 paragraph summary written for the target age",
  "fun_facts": ["3 to 5 short fun facts a child would enjoy"],
  "why_inspiring": "One short paragraph: why this person inspires young readers"
}}
```

Only include facts you are confident are accurate. If you don't know a date, set `lifespan` to null.
No commentary."""

    async def write(
        self,
        person: DedicatedPersonality,
        target_age: int,
        extended_context: str | None = None,
    ) -> Biography:
        system = (
            "You are a children's nonfiction writer who turns the lives of remarkable "
            "people into short, accurate, inspiring stories for kids."
        )
        prompt = self._build_prompt(person, target_age, extended_context)
        response = await self._model.generate(prompt, system, temperature=0.4)
        data = parse_json_response(response, expect=dict)
        lifespan = data.get("lifespan")
        if isinstance(lifespan, str) and lifespan.strip().lower() in {
            "null",
            "none",
            "",
            "unknown",
        }:
            lifespan = None
        return Biography(
            name=data.get("name") or person.name,
            title=data["title"],
            lifespan=lifespan,
            one_line=data["one_line"],
            summary=data["summary"],
            fun_facts=[str(f) for f in data["fun_facts"]],
            why_inspiring=data["why_inspiring"],
        )


async def enrich_chapters(
    chapters: list[Chapter],
    target_age: int,
    learning_objectives: list[str],
    model: str | None = None,
) -> list[Chapter]:
    """Populate `chapter.reflection` for each chapter (sequential — LLMs share a client)."""
    agent = ReflectionGeneratorAgent(model=model)
    for chapter in chapters:
        chapter.reflection = await agent.generate_for_chapter(
            chapter, target_age, learning_objectives
        )
        logger.info(f"Reflection: chapter {chapter.number} → 3 questions")
    return chapters

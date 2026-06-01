"""Registry of AI content-improvement actions used by the Studio editor.

Each action maps a button in the UI to a system persona plus a user-prompt
builder. The frontend sends the field's current text and a small context object
(target age, chapter title, characters, ...); the backend runs it through
``EnhancedTextModel`` and returns improved text the author can accept or reject.

Keeping the prompts here (not in the API module) makes the catalogue easy to
read, extend, and unit-test in isolation.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

Context = dict[str, object]


@dataclass(frozen=True)
class AIAction:
    """One improvement action.

    Attributes:
        label: Human-readable button label shown in the UI.
        field: Field family this applies to (used by the UI to group actions):
            one of ``"prose"``, ``"poem"``, ``"reflection"``, ``"image_prompt"``,
            ``"caption"``, ``"metadata"``, ``"biography"``, ``"experiment"``.
        system: System persona for the LLM.
        template: Builds the user prompt from the current text and context.
        returns_list: When True, the model is asked for a JSON array and the API
            parses the response into a list (e.g. reflection questions).
    """

    label: str
    field: str
    system: str
    template: Callable[[str, Context], str]
    returns_list: bool = False


_EDITOR = (
    "You are an expert children's book editor. You write warm, vivid, "
    "age-appropriate prose for young readers and respect the author's voice. "
    "You return ONLY the requested text — no preamble, no quotation marks, no "
    "commentary."
)


def _age(ctx: Context) -> object:
    return ctx.get("target_age", 7)


def _scene(ctx: Context) -> str:
    bits = []
    if ctx.get("chapter_title"):
        bits.append(f"chapter '{ctx['chapter_title']}'")
    if ctx.get("characters"):
        chars = ", ".join(str(c) for c in ctx["characters"])  # type: ignore[arg-type]
        bits.append(f"characters: {chars}")
    return f" ({'; '.join(bits)})" if bits else ""


ACTIONS: dict[str, AIAction] = {
    "polish_prose": AIAction(
        label="Polish prose",
        field="prose",
        system=_EDITOR,
        template=lambda text, ctx: (
            f"Polish this chapter passage for a {_age(ctx)}-year-old reader{_scene(ctx)}. "
            "Improve flow, imagery, and rhythm while keeping the meaning, characters, "
            "and approximate length. Return the revised passage only:\n\n"
            f"{text}"
        ),
    ),
    "tighten": AIAction(
        label="Tighten",
        field="prose",
        system=_EDITOR,
        template=lambda text, ctx: (
            f"Tighten this passage for a {_age(ctx)}-year-old reader{_scene(ctx)}. "
            "Cut padding and repetition, keep every story beat and the voice. "
            "Return the tightened passage only:\n\n"
            f"{text}"
        ),
    ),
    "age_adjust": AIAction(
        label="Fit the age",
        field="prose",
        system=_EDITOR,
        template=lambda text, ctx: (
            f"Rewrite this passage so vocabulary and sentence length suit a "
            f"{_age(ctx)}-year-old reader{_scene(ctx)}, without losing meaning or "
            "charm. Return the rewritten passage only:\n\n"
            f"{text}"
        ),
    ),
    "expand": AIAction(
        label="Expand",
        field="prose",
        system=_EDITOR,
        template=lambda text, ctx: (
            f"Expand this passage for a {_age(ctx)}-year-old reader{_scene(ctx)} with "
            "richer sensory detail and a little more action or dialogue, staying true "
            "to the voice. Return the expanded passage only:\n\n"
            f"{text}"
        ),
    ),
    "refine_poem": AIAction(
        label="Refine poem",
        field="poem",
        system=_EDITOR,
        template=lambda text, ctx: (
            f"Refine this short children's poem{_scene(ctx)} for a {_age(ctx)}-year-old. "
            "Improve rhythm and imagery, preserve its theme and line breaks. "
            "Return only the poem, with newlines preserved:\n\n"
            f"{text}"
        ),
    ),
    "reflection_questions": AIAction(
        label="Suggest 3 questions",
        field="reflection",
        system=_EDITOR,
        returns_list=True,
        template=lambda text, ctx: (
            f"Write exactly 3 open-ended reflection questions for a {_age(ctx)}-year-old "
            f"based on this chapter{_scene(ctx)}. They should spark curiosity and "
            "discussion, not have yes/no answers. Return a JSON array of 3 strings only:\n\n"
            f"{text}"
        ),
    ),
    "improve_image_prompt": AIAction(
        label="Improve image prompt",
        field="image_prompt",
        system=(
            "You write concise, vivid visual descriptions used as prompts for an "
            "illustration model in a children's book. Describe subject, setting, mood, "
            "lighting, and composition. Return ONLY the description."
        ),
        template=lambda text, ctx: (
            f"Improve this illustration description{_scene(ctx)} into a clearer, more "
            "evocative image-generation prompt for a children's storybook scene. "
            "Keep it a single descriptive paragraph. Return the description only:\n\n"
            f"{text}"
        ),
    ),
    "write_caption": AIAction(
        label="Write caption",
        field="caption",
        system=_EDITOR,
        template=lambda text, ctx: (
            f"Write a short, warm caption (max ~12 words) in the story's voice for an "
            f"illustration{_scene(ctx)} described as:\n\n{text}\n\nReturn the caption only."
        ),
    ),
    "suggest_tagline": AIAction(
        label="Suggest tagline",
        field="metadata",
        system=_EDITOR,
        template=lambda text, ctx: (
            "Write a short, catchy marketing tagline (max ~10 words) for this "
            f"children's book for {_age(ctx)}-year-olds. Title/premise:\n\n{text}\n\n"
            "Return the tagline only."
        ),
    ),
    "suggest_premise": AIAction(
        label="Suggest premise",
        field="metadata",
        system=_EDITOR,
        template=lambda text, ctx: (
            "Write a one-sentence story premise (a back-cover hook) for this children's "
            f"book for {_age(ctx)}-year-olds, based on:\n\n{text}\n\nReturn the sentence only."
        ),
    ),
    "polish_biography": AIAction(
        label="Polish summary",
        field="biography",
        system=_EDITOR,
        template=lambda text, ctx: (
            f"Polish this short biography summary so it reads warmly and clearly for a "
            f"{_age(ctx)}-year-old, in 2-3 short paragraphs. Keep all facts. "
            "Return the summary only:\n\n"
            f"{text}"
        ),
    ),
    "refine_experiment": AIAction(
        label="Refine steps",
        field="experiment",
        system=_EDITOR,
        template=lambda text, ctx: (
            f"Refine these hands-on activity steps for a {_age(ctx)}-year-old (with adult "
            "help). Make each step clear and safe. Return a JSON array of step strings only:\n\n"
            f"{text}"
        ),
        returns_list=True,
    ),
}

"""Image prompt builders.

Goal: maximise character consistency across every illustration in a book.

Strategy:
1. Build a **strict identity block** per character — heritage, age, distinctive
   features, clothing — that is used VERBATIM in every prompt that includes that
   character. This is the text-level anchor.
2. Stack the prompt in a fixed order so the model latches onto identity, then
   scene, then style. Order matters for diffusion models.
3. Keep style/motif language separate from identity language so the two don't
   bleed into each other.

The visual-level anchor (IP-Adapter feeding canonical reference images) is wired
in `models/image.py`; this module only owns the text.
"""

from __future__ import annotations

from fable_flow.schemas.book_content import IllustrationSpec
from fable_flow.schemas.input_spec import Character

# Anti-text directive.
#
# FLUX 1 and FLUX 2 expose no negative-prompt parameter — the only lever for
# suppressing text artifacts is the positive prompt. Diffusion models also
# weight the EARLY tokens of the prompt more heavily than later ones, so we
# prepend this directive to every image prompt. Phrased positively ("pure
# visual artwork…") because models follow positive cues better than negations
# like "no text".
NO_TEXT_DIRECTIVE = (
    "Pure visual artwork — wordless illustration with no text, no letters, no words, "
    "no typography, no captions, no titles, no signatures, no watermarks, no logos, "
    "no readable script of any kind anywhere in the image. "
    "Empty surfaces stay empty; signs, posters and labels are blank."
)

# Negative-prompt terms (SDXL / SD3 only — FLUX ignores negative prompts).
# Expanded with text-specific terms beyond the general negatives.
_NEGATIVE_TEXT_TERMS = (
    "text, letters, words, typography, captions, titles, signatures, "
    "watermarks, logos, writing, handwriting, script, lettering, fonts, "
    "subtitles, labels, signs with words, posters with words, "
    "newspapers, embedded text, ASCII, alphabet, characters, glyphs, "
    "books with visible text, readable script"
)


def build_identity_block(char: Character) -> str:
    """One-line identity anchor for `char`. Stable across every prompt.

    Format is fixed so the model sees the same string each time the character
    appears. Even small word-order changes can change the generated face — we
    don't allow them.
    """
    parts = [char.name]
    if char.age is not None:
        parts.append(f"{char.age}-year-old")
    parts.extend(
        [
            char.appearance.heritage,
            "child" if char.age and char.age <= 12 else "person",
            f"with {char.appearance.skin_tone} skin",
            char.appearance.hair + " hair",
            char.appearance.eyes + " eyes",
        ]
    )
    if char.appearance.distinctive_features:
        parts.append("(" + ", ".join(char.appearance.distinctive_features) + ")")
    parts.append(f"wearing {char.typical_clothing}")
    return ", ".join(parts)


def build_scene_characters_block(
    characters_in_scene: list[str],
    full_cast: list[Character],
) -> str:
    """Pick the identity blocks for characters actually in this scene."""
    by_name = {c.name: c for c in full_cast}
    blocks = []
    for name in characters_in_scene:
        if name in by_name:
            blocks.append(build_identity_block(by_name[name]))
    if not blocks:
        return ""
    return "Characters in this image:\n" + "\n".join(f"  - {b}" for b in blocks)


def build_style_anchor(
    illustration_style: str,
    motifs: list[str] | None = None,
) -> str:
    """Style guidance, kept separate from identity for clean signal."""
    parts = [
        f"Art style: {illustration_style}.",
        "Children's picture book illustration, soft lighting, expressive faces, "
        "warm colour palette, gentle composition.",
    ]
    if motifs:
        parts.append(
            "Subtle recurring motifs to weave in where they fit naturally: " + "; ".join(motifs)
        )
    return " ".join(parts)


def build_negative_prompt(target_age: int) -> str:
    """Negative prompt for models that accept one (SDXL, SD3; FLUX ignores)."""
    return (
        f"{_NEGATIVE_TEXT_TERMS}, "
        "scary, dark, gloomy, horror, frightening, blood, weapons, violence, "
        "deformed face, distorted features, extra limbs, extra fingers, "
        "low quality, blurry, "
        f"inappropriate for {target_age}-year-old reader"
    )


def build_portrait_prompt(char: Character, illustration_style: str) -> str:
    """Canonical portrait of `char` — used as the IP-Adapter reference."""
    identity = build_identity_block(char)
    return (
        f"{NO_TEXT_DIRECTIVE} "
        f"Children's-book character reference portrait. {identity}. "
        "Centered head-and-shoulders portrait, neutral friendly expression, "
        "plain soft pastel background, even lighting, looking slightly toward the camera. "
        f"Art style: {illustration_style}. Single character only, no other people, no border."
    )


def build_full_body_prompt(char: Character, illustration_style: str) -> str:
    """Canonical full-body — used as a secondary reference for action shots."""
    identity = build_identity_block(char)
    return (
        f"{NO_TEXT_DIRECTIVE} "
        f"Children's-book character reference, full body, standing pose. {identity}. "
        "Standing relaxed, slight smile, looking forward, "
        "plain soft pastel background, even lighting. "
        f"Art style: {illustration_style}. Single character only, no other people, no border."
    )


def build_scene_prompt(
    spec: IllustrationSpec,
    full_cast: list[Character],
    illustration_style: str,
    motifs: list[str] | None = None,
) -> str:
    """Compose the scene-illustration prompt with strict ordering.

    Order: anti-text → identity → scene description → composition → style/motifs.
    Diffusion models weight early tokens more, so the anti-text directive leads.
    """
    chars_block = build_scene_characters_block(spec.characters, full_cast)

    sections = [
        # Anti-text leads so FLUX (which has no negative prompt) sees it strongly.
        NO_TEXT_DIRECTIVE,
        # Identity next.
        chars_block if chars_block else "",
        # Then the scene.
        f"Scene: {spec.description}",
        f"Setting: {spec.scene_context}.",
        # Composition guidance.
        (
            "Composition: rule of thirds, characters facing or interacting with "
            "the scene focus, expressive faces visible, age-appropriate framing."
        ),
        # Style last so identity dominates the early latents.
        build_style_anchor(illustration_style, motifs),
    ]
    return " ".join(s for s in sections if s).strip()


def build_scene_prompt_for_movie(
    scene_text: str,
    setting: str,
    mood: str,
    characters_in_scene: list[str],
    full_cast: list[Character],
    illustration_style: str,
) -> str:
    """Movie-scene image prompt (16:9 cinematic). Used when no book illustration matches."""
    chars_block = build_scene_characters_block(characters_in_scene, full_cast)
    sections = [
        NO_TEXT_DIRECTIVE,
        chars_block,
        f"Scene: {scene_text.strip()}",
        f"Setting: {setting}. Mood: {mood}.",
        (
            "Composition: 16:9 cinematic frame, characters clearly visible, "
            "rule of thirds, soft natural lighting."
        ),
        build_style_anchor(illustration_style),
    ]
    return " ".join(s for s in sections if s).strip()

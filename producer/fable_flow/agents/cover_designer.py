"""CoverDesignerAgent — generates front + back cover images.

Pipeline:
1. Build deterministic prompts (no text in image) from book metadata.
2. Generate text-free illustrations via the image model with a stable seed
   derived from the title (so a given book always produces the same artwork).
3. Composite title / author / tagline / blurb text over the illustrations using
   PIL — text lives in the overlay, never in the diffusion output, because
   diffusion models render letterforms badly.

Output: a `CoverImages` record plus PNG files on disk. Resumable: existing
composited files are reused when `resume=True`.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import textwrap
from io import BytesIO
from pathlib import Path

from loguru import logger
from PIL import Image, ImageDraw, ImageFont

from fable_flow.agents._image_prompts import NO_TEXT_DIRECTIVE, build_identity_block
from fable_flow.config import config
from fable_flow.schemas.book_content import BookContent, CoverImages
from fable_flow.schemas.input_spec import Character, CharacterRole

# Cover artwork is generated at portrait 2:3 (matches a 6×9 trade paperback).
COVER_WIDTH = 1024
COVER_HEIGHT = 1536

# Font fallback chain. Order: hardcoded path → fc-match query → fallback family.
# Many minimal Linux installs ship only DejaVu Sans/Serif Regular + Bold
# (no italic, no oblique). When the requested style is missing, we fall back
# to the regular variant of the same family — the visual hit is minor and far
# better than dropping to PIL's bitmap default at fixed size.
_FONT_CANDIDATES: dict[str, list[str]] = {
    "serif_bold": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSerif-Bold.ttf",
        "/usr/share/fonts/liberation-serif/LiberationSerif-Bold.ttf",
        "/usr/share/fonts/liberation/LiberationSerif-Bold.ttf",
        "/usr/share/fonts/noto/NotoSerif-Bold.ttf",
        "/usr/share/fonts/TTF/DejaVuSerif-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
        "/Library/Fonts/Georgia Bold.ttf",
    ],
    "serif_italic": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf",
        "/usr/share/fonts/dejavu/DejaVuSerif-Italic.ttf",
        "/usr/share/fonts/liberation-serif/LiberationSerif-Italic.ttf",
        "/usr/share/fonts/liberation/LiberationSerif-Italic.ttf",
        "/usr/share/fonts/noto/NotoSerif-Italic.ttf",
        "/usr/share/fonts/TTF/DejaVuSerif-Italic.ttf",
        "/System/Library/Fonts/Supplemental/Georgia Italic.ttf",
    ],
    "serif": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        "/usr/share/fonts/dejavu/DejaVuSerif.ttf",
        "/usr/share/fonts/liberation-serif/LiberationSerif-Regular.ttf",
        "/usr/share/fonts/liberation/LiberationSerif-Regular.ttf",
        "/usr/share/fonts/noto/NotoSerif-Regular.ttf",
        "/usr/share/fonts/TTF/DejaVuSerif.ttf",
        "/System/Library/Fonts/Supplemental/Georgia.ttf",
    ],
    "sans": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/liberation-sans/LiberationSans-Regular.ttf",
        "/usr/share/fonts/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Helvetica.ttc",
    ],
}

# fontconfig queries used when no hardcoded path is found. `fc-match` ships
# with most Linux distributions and resolves a generic family query like
# "serif:italic" to the best available system font.
_FONT_QUERIES: dict[str, list[str]] = {
    "serif_bold": ["serif:style=Bold", "serif:weight=bold"],
    "serif_italic": ["serif:style=Italic", "serif:slant=italic"],
    "serif": ["serif"],
    "sans": ["sans-serif"],
}

# When the requested style isn't installed, try the same family without the
# style modifier rather than collapsing to PIL's bitmap default.
_FAMILY_FALLBACKS: dict[str, list[str]] = {
    "serif_bold": ["serif_bold", "serif"],
    "serif_italic": ["serif_italic", "serif"],
    "serif": ["serif"],
    "sans": ["sans", "serif"],
}


def _try_fc_match(family_query: str) -> Path | None:
    """Resolve a fontconfig query (e.g. 'serif:italic') to a font file path.

    Returns None if fc-match isn't installed, times out, or returns a path
    that doesn't exist / isn't a TTF/OTF.
    """
    if shutil.which("fc-match") is None:
        return None
    try:
        result = subprocess.run(
            ["fc-match", "-f", "%{file}", family_query],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    path = Path(result.stdout.strip())
    if path.exists() and path.suffix.lower() in (".ttf", ".otf"):
        return path
    return None


def _load_font(family: str, size: int) -> ImageFont.ImageFont:
    """Resolve `family` to a real TTF, walking fallbacks.

    Order: hardcoded paths for the exact family → fc-match query for it →
    hardcoded paths for the family-fallback (e.g. serif when serif_italic
    is missing) → fc-match query for the fallback → PIL bitmap default.

    Logs at info level when we fall back to a less-ideal variant; warns only
    on the true last-resort PIL default (which renders poorly).
    """
    chain = _FAMILY_FALLBACKS.get(family, [family])
    for idx, candidate_family in enumerate(chain):
        for path in _FONT_CANDIDATES.get(candidate_family, []):
            if Path(path).exists():
                if idx > 0:
                    logger.info(f"Font {family!r} unavailable; using {candidate_family!r} ({path})")
                return ImageFont.truetype(path, size)
        for query in _FONT_QUERIES.get(candidate_family, []):
            found = _try_fc_match(query)
            if found is not None:
                if idx > 0:
                    logger.info(
                        f"Font {family!r} unavailable; using {candidate_family!r} "
                        f"via fc-match ({found})"
                    )
                return ImageFont.truetype(str(found), size)
    logger.warning(
        f"No system font found for {family!r} or its fallbacks; "
        "using PIL bitmap default (size hint ignored, text will look poor)"
    )
    return ImageFont.load_default()


def _stable_seed(text: str) -> int:
    """Hash → 31-bit int. Same `text` always yields the same seed."""
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") & 0x7FFFFFFF


def _draw_outlined_centered(
    draw: ImageDraw.ImageDraw,
    text: str,
    y: int,
    font: ImageFont.ImageFont,
    image_width: int,
    fill: tuple[int, int, int] = (255, 255, 255),
    stroke_fill: tuple[int, int, int] = (12, 12, 18),
    stroke_width: int = 3,
) -> int:
    """Draw `text` centered at `y` with a clean PIL stroke outline.

    PIL's `stroke_width` / `stroke_fill` produces crisp anti-aliased letter
    outlines — this is what professional book-cover typography uses. The old
    "draw 8 offset shadow copies" trick blurs glyphs and creates the swimming
    halo effect we want to avoid.
    """
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (image_width - text_w) // 2 - bbox[0]
    draw.text(
        (x, y),
        text,
        font=font,
        fill=fill,
        stroke_width=stroke_width,
        stroke_fill=stroke_fill,
    )
    return y + text_h


def _draw_wrapped_outlined(
    draw: ImageDraw.ImageDraw,
    text: str,
    y: int,
    font: ImageFont.ImageFont,
    image_width: int,
    max_chars_per_line: int,
    line_spacing: int = 6,
    fill: tuple[int, int, int] = (255, 255, 255),
    stroke_fill: tuple[int, int, int] = (12, 12, 18),
    stroke_width: int = 3,
) -> int:
    for line in textwrap.wrap(text, width=max_chars_per_line):
        y = _draw_outlined_centered(
            draw,
            line,
            y,
            font,
            image_width,
            fill=fill,
            stroke_fill=stroke_fill,
            stroke_width=stroke_width,
        )
        y += line_spacing
    return y


def _add_gradient_panel(
    image: Image.Image,
    y_top: int,
    y_bottom: int,
    alpha: int = 170,
    fade: str = "bottom",
) -> None:
    """Darken a vertical band with a soft gradient fade at one edge.

    `fade="bottom"` → solid at top, fades to transparent at the bottom edge
    (use behind a top title block). `fade="top"` is the mirror image (use
    behind a bottom author/blurb block). `fade="none"` is a solid band.
    """
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    h_band = max(1, y_bottom - y_top)
    fade_zone = max(20, h_band // 3)
    w = image.size[0]
    for i in range(h_band):
        if fade == "bottom" and i >= h_band - fade_zone:
            a = int(alpha * (h_band - i) / fade_zone)
        elif fade == "top" and i < fade_zone:
            a = int(alpha * i / fade_zone)
        else:
            a = alpha
        overlay_draw.line([(0, y_top + i), (w, y_top + i)], fill=(0, 0, 0, a))
    image.alpha_composite(overlay)


def _draw_card(
    image: Image.Image,
    x: int,
    y: int,
    w: int,
    h: int,
    radius: int = 24,
    fill: tuple[int, int, int, int] = (15, 18, 28, 210),
    border: tuple[int, int, int, int] = (255, 255, 255, 80),
) -> None:
    """Draw a translucent rounded card with a hairline border.

    Used for the back-cover blurb block — keeps copy contained in one tidy
    rectangle rather than darkening 70% of the illustration.
    """
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rounded_rectangle(
        [(x, y), (x + w, y + h)],
        radius=radius,
        fill=fill,
        outline=border,
        width=2,
    )
    image.alpha_composite(overlay)


def _line_height(font: ImageFont.ImageFont, leading: float = 1.25) -> int:
    """Approximate line height: ascent + descent scaled by leading."""
    if hasattr(font, "getmetrics"):
        ascent, descent = font.getmetrics()
        return int((ascent + descent) * leading)
    return int(font.size * leading) if hasattr(font, "size") else 24


def _wrap_to_width(
    text: str,
    font: ImageFont.ImageFont,
    max_width: int,
    draw: ImageDraw.ImageDraw,
) -> list[str]:
    """Wrap `text` so no line is wider than `max_width` pixels (real measurement)."""
    words = text.split()
    if not words:
        return []
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        trial = f"{current} {word}"
        bbox = draw.textbbox((0, 0), trial, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = trial
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _shared_visual_context(book: BookContent) -> str:
    """Visual atmosphere shared verbatim by BOTH cover prompts.

    Front and back covers must read as companion pieces, not as unrelated
    artwork. The way to get that from a diffusion model is to use the exact
    same phrasing for palette, lighting, style, and setting in both prompts
    — small wording differences nudge the model toward different palettes.

    This block covers: art style + lighting mood + palette + setting hint.
    """
    style = config.style.illustration_style
    setting_hint = (
        book.biography.one_line.rstrip(".")
        if book.biography
        else (book.metadata.subtitle or book.metadata.tagline or book.metadata.genre)
    )
    return (
        f"Art style: {style}. Warm golden-hour lighting with soft amber and "
        "butter-yellow highlights and gentle blue-green shadow tints. Painterly "
        "watercolor cohesion, rich saturated palette, magical and inviting. "
        f"World / setting evokes: {setting_hint}."
    )


def _build_front_prompt(
    book: BookContent,
    protagonist: Character | None = None,
) -> str:
    """Front cover artwork prompt — deterministic, NO text in image.

    Crucial design rules (the hard lessons of getting text out of diffusion):

    1. NEVER say "book cover" or "cover" — these words are the single strongest
       trigger for the model to render title typography. Diffusion's training
       set is full of real book covers with text, so "book cover" reliably
       produces letters even with strong negative prompting.
    2. NEVER quote the book title — quoted strings often get rendered as text.
       The title is added later by PIL overlay; the diffusion prompt only
       needs the visual SUBJECT, not the wording.
    3. Frame as a "wordless painting" / "art print" — formats with no learned
       text association.
    4. Explicitly list text-bearing objects (signs, banners, books, scrolls,
       papers, screens) as things NOT to include — these are common failure
       modes where text appears on objects inside the scene.

    Character identity (NEW): when `protagonist` is a full `Character` object,
    its appearance fields (heritage, skin tone, hair, eyes, distinctive
    features, clothing) are folded in verbatim via `build_identity_block` —
    the same anchor used by chapter illustrations, so the cover protagonist
    matches the in-book character instead of looking like a generic kid.
    """
    meta = book.metadata
    audience = f"{meta.target_age}-year-old children"

    # Protagonist identity — rich block when we have a Character, falls back to
    # just the name from character_references, falls back to "a young child".
    if protagonist is not None:
        protag_descr = f"the protagonist — {build_identity_block(protagonist)}"
    elif book.character_references:
        protag_descr = f"a young child named {book.character_references[0].name}"
    else:
        protag_descr = "a young child"

    # Activity / scene to depict — prefer the biography one-liner because it's
    # a concrete action ("she taught computers to see") rather than a generic
    # mood word.
    activity = (
        (book.biography.one_line if book.biography else None)
        or meta.subtitle
        or meta.tagline
        or meta.genre
    )

    if book.biography is not None:
        bio = book.biography
        subject = (
            f"{protag_descr}, together with {bio.name} ({bio.title}). The two of them "
            f"engaged in the scene of: {activity.rstrip('.')}. Show both characters clearly, "
            "interacting around the activity. The child's appearance MUST match the identity "
            "description above exactly — same heritage, skin tone, hair colour, eye colour, "
            "and clothing — and stay consistent with the character reference image."
        )
    else:
        subject = (
            f"{protag_descr}, engaged in the scene of: {activity.rstrip('.')}. "
            "The child's appearance MUST match the identity description above exactly — "
            "same heritage, skin tone, hair colour, eye colour, and clothing — and stay "
            "consistent with the character reference image."
        )

    shared = _shared_visual_context(book)
    return (
        f"{NO_TEXT_DIRECTIVE} "
        f"Wordless watercolor painting depicting {subject} "
        f"Painted for {audience}. "
        "Portrait 2:3 aspect ratio composition, hero subjects in the middle two thirds, "
        "calm uncluttered painted background at top and bottom — leave those areas as plain sky, "
        "soft gradient, atmospheric wash, or simple foliage. "
        "DO NOT include any signs, banners, posters, billboards, labels, open notebooks, "
        "open scrolls, sheets of paper, computer screens, phone screens, chalkboards, "
        "whiteboards, or any other surface that typically carries writing. "
        f"{shared} "
        "This is a pure painted artwork in the style of wall art, an art print, "
        "or a gallery painting. Absolutely no embedded typography, "
        "no logos, no signatures anywhere."
    )


def _build_back_prompt(book: BookContent) -> str:
    """Back cover artwork — visual COMPANION piece extending the front cover.

    Visual continuity is enforced two ways:
    1. The exact same `_shared_visual_context` clause (palette, lighting,
       style, setting) appears in both prompts — same words to the model →
       same palette out of the model.
    2. Explicit framing: "companion piece to the matching front-cover painting
       of the same book. Share the EXACT same colour palette and lighting."
       Without this, the model treats the back as an unrelated landscape.

    Composition still differs: front = hero shot of characters, back = wide
    establishing view of the same world with characters distant or absent
    (so the blurb overlay has clean space to sit in).
    """
    meta = book.metadata
    motif_hint = meta.tagline or meta.subtitle or meta.genre
    shared = _shared_visual_context(book)

    return (
        f"{NO_TEXT_DIRECTIVE} "
        "Wordless atmospheric landscape painting — the visual COMPANION piece to the "
        "matching hero portrait painting it pairs with. Share the EXACT same colour "
        "palette, lighting mood, time of day, and painterly style as that hero painting. "
        "This is an extension of the same painted world — same horizon, same atmosphere. "
        # Strong character-exclusion language: when the front image is fed in as
        # visual reference, the model is tempted to repeat the characters in
        # the back. These instructions tell it to inherit palette+light ONLY.
        "Inherit from the reference image ONLY the colour palette, lighting, brushwork, "
        "and atmosphere — DO NOT include the people, faces, or characters from the "
        "reference. This is pure landscape: no human figures in the foreground, no "
        "portraits, no close-up faces. If any figures appear at all they are tiny, "
        "distant, and unrecognisable. "
        "Composition: a quiet wide establishing view of that world from further away, "
        "environment-led, empty foreground. "
        "Large uncluttered painted sky, wash, or simple landscape in the upper two thirds — "
        "keep that area as plain atmospheric background for a blurb text overlay. "
        f"Mood / motif: {motif_hint.rstrip('.')}. Portrait 2:3 aspect ratio. "
        "DO NOT include any signs, banners, posters, billboards, labels, open notebooks, "
        "open scrolls, sheets of paper, computer screens, phone screens, chalkboards, "
        "whiteboards, or any other surface that typically carries writing. "
        f"{shared} "
        "This is a pure painted artwork in the style of wall art, an art print, "
        "or a landscape painting. Absolutely no embedded typography, "
        "no logos, no signatures anywhere."
    )


def _compose_back_blurb(book: BookContent) -> list[str]:
    """Assemble back-cover text blocks deterministically from book metadata.

    Order: tagline → premise (or fallback) → audience line → series line.
    Blank strings dropped; never invents copy that isn't in metadata.
    """
    meta = book.metadata
    blocks: list[str] = []
    if meta.tagline:
        blocks.append(f'"{meta.tagline}"')
    if meta.premise:
        blocks.append(meta.premise)
    elif meta.subtitle:
        blocks.append(meta.subtitle)
    blocks.append(f"A {meta.genre} story for {meta.target_age}-year-old readers.")
    if meta.series:
        series_line = meta.series + (f", Volume {meta.volume}" if meta.volume else "")
        blocks.append(series_line)
    return blocks


def _scale_title_size(title: str, base_size: int) -> int:
    """Pick a title font size that fits the cover without crushing.

    Long titles (5+ words) get scaled down 10–25% so they don't wrap to 4 lines.
    """
    n_words = len(title.split())
    if n_words <= 3:
        return base_size
    if n_words <= 5:
        return int(base_size * 0.92)
    if n_words <= 8:
        return int(base_size * 0.82)
    return int(base_size * 0.72)


def _overlay_front_text(base: Image.Image, book: BookContent) -> Image.Image:
    """Render series / title / subtitle / author over the front illustration.

    Layout follows a real children's-book-cover grid:

        ┌─────────────────────┐  ← top gradient panel (fades into the art)
        │   SERIES · VOL N    │  small caps, sans, light grey
        │                     │
        │   THE TITLE GOES    │  large bold serif, outlined for legibility
        │       HERE          │
        │                     │
        │  italic subtitle    │  italic serif, smaller
        ├─────────────────────┤
        │      [artwork]      │
        ├─────────────────────┤
        │      Author Name    │  sans, on bottom gradient panel
        └─────────────────────┘

    All text uses PIL's `stroke_width` outline for crisp letterforms — the
    halo-shadow approach this replaces produced fuzzy / swimming glyphs.
    """
    image = base.convert("RGBA").copy()
    w, h = image.size
    meta = book.metadata
    draw = ImageDraw.Draw(image)

    # Fonts — title size adapts to title length so long titles don't wrap to 4 lines.
    title_size = _scale_title_size(meta.title, base_size=int(w * 0.085))
    title_font = _load_font("serif_bold", size=title_size)
    subtitle_font = _load_font("serif_italic", size=int(w * 0.038))
    series_font = _load_font("sans", size=int(w * 0.028))
    author_font = _load_font("sans", size=int(w * 0.040))

    # ---- TOP BLOCK (series + title + subtitle) ----
    side_margin = int(w * 0.06)
    title_max_width = w - 2 * side_margin
    title_lines = _wrap_to_width(meta.title, title_font, title_max_width, draw)
    subtitle_lines = (
        _wrap_to_width(meta.subtitle, subtitle_font, title_max_width, draw) if meta.subtitle else []
    )

    # Measure block height to size the gradient panel just-large-enough.
    top_padding = int(h * 0.05)
    series_h = _line_height(series_font) + 14 if meta.series else 0
    title_block_h = len(title_lines) * (_line_height(title_font, leading=1.10))
    subtitle_block_h = (
        len(subtitle_lines) * _line_height(subtitle_font, leading=1.20) + int(h * 0.015)
        if subtitle_lines
        else 0
    )
    top_panel_h = top_padding + series_h + title_block_h + subtitle_block_h + int(h * 0.03)

    _add_gradient_panel(image, 0, top_panel_h, alpha=180, fade="bottom")
    draw = ImageDraw.Draw(image)

    y = top_padding
    if meta.series:
        series_line = meta.series.upper() + (f"   ·   VOLUME {meta.volume}" if meta.volume else "")
        y = _draw_outlined_centered(
            draw, series_line, y, series_font, w, fill=(220, 220, 230), stroke_width=2
        )
        y += 14
    for line in title_lines:
        y = _draw_outlined_centered(draw, line, y, title_font, w, stroke_width=4)
        y += 2
    if subtitle_lines:
        y += int(h * 0.012)
        for line in subtitle_lines:
            y = _draw_outlined_centered(
                draw, line, y, subtitle_font, w, fill=(240, 235, 245), stroke_width=2
            )
            y += 4

    # ---- BOTTOM BLOCK (author) ----
    author_panel_top = int(h * 0.90)
    _add_gradient_panel(image, author_panel_top, h, alpha=170, fade="top")
    draw = ImageDraw.Draw(image)
    author_y = author_panel_top + int((h - author_panel_top - _line_height(author_font)) / 2)
    _draw_outlined_centered(draw, meta.author, author_y, author_font, w, stroke_width=2)

    return image.convert("RGB")


def _overlay_back_text(base: Image.Image, book: BookContent) -> Image.Image:
    """Render the back-cover blurb as a centered translucent content card.

    Layout: a single rounded-rectangle card sits in the upper-middle of the
    image. Tagline (italic, large) → premise / blurb paragraphs → series line
    (small, separated by a rule). Card has a hairline border + soft fill so
    the artwork still shows around it — far less heavy-handed than the
    previous full-width darkening band.
    """
    image = base.convert("RGBA").copy()
    w, h = image.size
    blocks = _compose_back_blurb(book)
    if not blocks:
        return image.convert("RGB")

    tagline_font = _load_font("serif_italic", size=int(w * 0.055))
    body_font = _load_font("serif", size=int(w * 0.035))
    meta_font = _load_font("sans", size=int(w * 0.026))

    # Card geometry — centered horizontally, top third vertically.
    card_x = int(w * 0.08)
    card_w = w - 2 * card_x
    card_padding_h = int(w * 0.06)
    card_padding_v = int(h * 0.04)
    inner_w = card_w - 2 * card_padding_h
    draw_dummy = ImageDraw.Draw(image)

    # Precompute the wrapped lines + per-line heights so we can size the card.
    section_specs: list[tuple[ImageFont.ImageFont, list[str], int, int]] = []
    series_text = book.metadata.series
    for idx, text in enumerate(blocks):
        is_tagline = idx == 0 and text.startswith('"')
        is_series_line = idx == len(blocks) - 1 and series_text
        if is_tagline:
            font, gap_after = tagline_font, int(h * 0.022)
        elif is_series_line:
            font, gap_after = meta_font, 0
        else:
            font, gap_after = body_font, int(h * 0.018)
        lines = _wrap_to_width(text, font, inner_w, draw_dummy)
        line_h = _line_height(font, leading=1.35)
        section_specs.append((font, lines, line_h, gap_after))

    text_h = sum(len(lines) * line_h + gap for _, lines, line_h, gap in section_specs)
    # The series line sits below a thin rule with its own breathing room.
    if series_text:
        text_h += int(h * 0.025)
    card_h = text_h + 2 * card_padding_v
    card_y = int(h * 0.10)

    _draw_card(image, card_x, card_y, card_w, card_h)
    draw = ImageDraw.Draw(image)

    y = card_y + card_padding_v
    for spec_idx, (font, lines, line_h, gap_after) in enumerate(section_specs):
        is_series_line = spec_idx == len(section_specs) - 1 and series_text
        # Thin rule above the series line for clear hierarchy.
        if is_series_line:
            rule_y = y + int(h * 0.010)
            rule_x_pad = int(card_w * 0.20)
            draw.line(
                [(card_x + rule_x_pad, rule_y), (card_x + card_w - rule_x_pad, rule_y)],
                fill=(255, 255, 255, 110),
                width=1,
            )
            y += int(h * 0.025)
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            line_w = bbox[2] - bbox[0]
            x = card_x + (card_w - line_w) // 2 - bbox[0]
            draw.text((x, y), line, font=font, fill=(245, 240, 235))
            y += line_h
        y += gap_after

    return image.convert("RGB")


class CoverDesignerAgent:
    """Generate text-free cover illustrations and overlay book metadata on them."""

    def __init__(self, image_model, output_dir: Path | None = None) -> None:
        self.image_model = image_model
        self.output_dir = output_dir or Path("output")
        self.covers_dir = self.output_dir / "covers"
        self.covers_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _resolve_protagonist(
        book: BookContent,
        characters: list[Character] | None,
        protagonist_name: str | None,
    ) -> Character | None:
        """Find the `Character` to feature: explicit name → protagonist role → None."""
        if not characters:
            return None
        if protagonist_name:
            match = next((c for c in characters if c.name == protagonist_name), None)
            if match is not None:
                return match
        match = next((c for c in characters if c.role == CharacterRole.PROTAGONIST), None)
        if match is not None:
            return match
        # Last-resort: align with character_references ordering used in the prompt fallback.
        if book.character_references:
            first_ref_name = book.character_references[0].name
            return next((c for c in characters if c.name == first_ref_name), None)
        return None

    @staticmethod
    def _portrait_ref_for(book: BookContent, protagonist: Character | None) -> Path | None:
        """Resolve the protagonist's portrait reference path (if one exists on disk)."""
        if protagonist is None:
            return None
        for ref in book.character_references:
            if ref.name == protagonist.name and ref.portrait_path:
                p = Path(ref.portrait_path)
                if p.exists():
                    return p
        return None

    async def design_covers(
        self,
        book: BookContent,
        characters: list[Character] | None = None,
        protagonist_name: str | None = None,
        resume: bool = False,
    ) -> CoverImages:
        """Design front + back covers.

        `characters`: full character list from the input spec — used to thread
            appearance details (heritage, skin tone, hair, eyes, clothing) into
            the cover prompt so the protagonist actually looks like the
            in-book character instead of a random kid.
        `protagonist_name`: explicit name to feature; falls back to the first
            `CharacterRole.PROTAGONIST` in `characters`, then to the first
            `character_references` entry.

        When the protagonist has a portrait reference image on disk it is fed
        to the image model as visual conditioning (native `image=` on FLUX 2,
        IP-Adapter on FLUX 1 / SDXL) — combining text identity + image
        conditioning is what makes the cover character recognisable.
        """
        protagonist = self._resolve_protagonist(book, characters, protagonist_name)
        portrait_ref_path = self._portrait_ref_for(book, protagonist)

        front_base = self.covers_dir / "front_base.png"
        back_base = self.covers_dir / "back_base.png"
        front_final = self.covers_dir / "front.png"
        back_final = self.covers_dir / "back.png"

        if resume and front_final.exists() and back_final.exists():
            logger.info("Cover: reusing existing composited covers")
            return CoverImages(
                front_path=str(front_final),
                back_path=str(back_final),
                front_base_path=str(front_base) if front_base.exists() else None,
                back_base_path=str(back_base) if back_base.exists() else None,
            )

        title_seed = _stable_seed(book.metadata.title)

        if resume and front_base.exists():
            logger.info("Cover: reusing front base illustration")
            front_image = Image.open(front_base).convert("RGBA")
        else:
            front_prompt = _build_front_prompt(book, protagonist=protagonist)
            if portrait_ref_path is not None:
                logger.info(
                    f"Cover: generating front illustration (conditioned on {portrait_ref_path})"
                )
                front_bytes = await self.image_model.generate_with_reference(
                    prompt=front_prompt,
                    reference_image_path=str(portrait_ref_path),
                    width=COVER_WIDTH,
                    height=COVER_HEIGHT,
                    seed=title_seed,
                )
            else:
                logger.info("Cover: generating front illustration (no portrait reference)")
                front_bytes = await self.image_model.generate_image(
                    prompt=front_prompt,
                    width=COVER_WIDTH,
                    height=COVER_HEIGHT,
                    seed=title_seed,
                )
            front_base.write_bytes(front_bytes)
            front_image = Image.open(BytesIO(front_bytes)).convert("RGBA")

        if resume and back_base.exists():
            logger.info("Cover: reusing back base illustration")
            back_image = Image.open(back_base).convert("RGBA")
        else:
            back_prompt = _build_back_prompt(book)
            back_seed = _stable_seed(book.metadata.title + "::back")
            if front_base.exists():
                # Use the just-generated FRONT as visual reference for the BACK.
                # This is the strongest lever for palette / lighting / style
                # continuity — image conditioning propagates the painted world's
                # colours, brushwork, and time-of-day directly into the back.
                # The back prompt has strong "do NOT include people from the
                # reference" language to keep the back as a clean landscape
                # despite the front containing characters.
                logger.info(
                    f"Cover: generating back illustration (conditioned on {front_base.name})"
                )
                back_bytes = await self.image_model.generate_with_reference(
                    prompt=back_prompt,
                    reference_image_path=str(front_base),
                    width=COVER_WIDTH,
                    height=COVER_HEIGHT,
                    seed=back_seed,
                )
            else:
                logger.info("Cover: generating back illustration (no front reference)")
                back_bytes = await self.image_model.generate_image(
                    prompt=back_prompt,
                    width=COVER_WIDTH,
                    height=COVER_HEIGHT,
                    seed=back_seed,
                )
            back_base.write_bytes(back_bytes)
            back_image = Image.open(BytesIO(back_bytes)).convert("RGBA")

        logger.info("Cover: compositing front overlay")
        _overlay_front_text(front_image, book).save(front_final, format="PNG")
        logger.info("Cover: compositing back overlay")
        _overlay_back_text(back_image, book).save(back_final, format="PNG")

        return CoverImages(
            front_path=str(front_final),
            back_path=str(back_final),
            front_base_path=str(front_base),
            back_base_path=str(back_base),
        )

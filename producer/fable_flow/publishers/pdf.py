"""Render BookContent to a print-ready PDF."""

from __future__ import annotations

from pathlib import Path

from loguru import logger
from PIL import Image as PILImage
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    HRFlowable,
    Image,
    KeepTogether,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
)

from fable_flow.config import config
from fable_flow.publishers._markdown import to_pdf
from fable_flow.schemas.book_content import (
    Biography,
    BookContent,
    Chapter,
    Experiment,
    IllustrationSpec,
)


def _build_styles() -> dict[str, ParagraphStyle]:
    cfg = config.pdf
    base_size = cfg.body_font_size
    body = ParagraphStyle(
        name="Body",
        fontName=cfg.body_font,
        fontSize=base_size,
        leading=base_size * cfg.line_height,
        textColor=HexColor(cfg.body_color),
        alignment=TA_LEFT,
        firstLineIndent=18,
        spaceAfter=6,
    )
    title = ParagraphStyle(
        name="Title",
        fontName=cfg.title_font,
        fontSize=cfg.title_font_size,
        leading=cfg.title_font_size * 1.2,
        textColor=HexColor(cfg.title_color),
        alignment=TA_CENTER,
        spaceAfter=20,
    )
    chapter = ParagraphStyle(
        name="ChapterHeading",
        fontName=cfg.title_font,
        fontSize=cfg.chapter_font_size,
        leading=cfg.chapter_font_size * 1.3,
        textColor=HexColor(cfg.chapter_color),
        alignment=TA_CENTER,
        spaceAfter=18,
    )
    caption = ParagraphStyle(
        name="Caption",
        fontName=cfg.body_font,
        fontSize=base_size - 2,
        leading=(base_size - 2) * 1.2,
        textColor=HexColor("#5D4E75"),
        alignment=TA_CENTER,
        spaceBefore=4,
        spaceAfter=12,
    )
    poem = ParagraphStyle(
        name="Poem",
        fontName="Times-Italic",  # elegant serif italic regardless of body font
        fontSize=base_size + 1,
        leading=(base_size + 1) * 1.7,  # extra line height for verse breathing room
        textColor=HexColor("#5D4E75"),  # muted purple — set apart from body
        alignment=TA_CENTER,
        spaceBefore=4,
        spaceAfter=4,
        leftIndent=60,
        rightIndent=60,
    )
    poem_ornament = ParagraphStyle(
        name="PoemOrnament",
        fontName=cfg.body_font,
        fontSize=base_size + 4,
        leading=(base_size + 4) * 1.4,
        textColor=HexColor("#B6A4CD"),  # soft lavender, lighter than poem text
        alignment=TA_CENTER,
        spaceBefore=10,
        spaceAfter=10,
    )
    meta = ParagraphStyle(
        name="Meta",
        fontName=cfg.body_font,
        fontSize=base_size,
        leading=base_size * cfg.line_height,
        textColor=HexColor(cfg.body_color),
        alignment=TA_CENTER,
        spaceAfter=6,
    )
    section_heading = ParagraphStyle(
        name="SectionHeading",
        fontName=cfg.title_font,
        fontSize=base_size + 2,
        leading=(base_size + 2) * 1.3,
        textColor=HexColor(cfg.chapter_color),
        alignment=TA_LEFT,
        spaceBefore=18,
        spaceAfter=10,
    )
    list_item = ParagraphStyle(
        name="ListItem",
        fontName=cfg.body_font,
        fontSize=base_size,
        leading=base_size * cfg.line_height,
        textColor=HexColor(cfg.body_color),
        alignment=TA_LEFT,
        leftIndent=18,
        spaceAfter=4,
    )
    toc_entry = ParagraphStyle(
        name="TocEntry",
        fontName=cfg.body_font,
        fontSize=base_size,
        leading=base_size * 1.6,
        textColor=HexColor(cfg.body_color),
        alignment=TA_LEFT,
        leftIndent=18,
        rightIndent=18,
        spaceAfter=4,
    )
    return {
        "body": body,
        "title": title,
        "chapter": chapter,
        "caption": caption,
        "meta": meta,
        "section_heading": section_heading,
        "list_item": list_item,
        "poem": poem,
        "poem_ornament": poem_ornament,
        "toc_entry": toc_entry,
    }


class _OutlineEntry(Flowable):
    """Invisible flowable — registers a PDF bookmark + outline entry at this point.

    Adds a destination addressable as `#<key>` (used by ToC links) and an entry
    in the PDF viewer's navigation/outline pane.
    """

    def __init__(self, key: str, label: str, level: int = 0) -> None:
        super().__init__()
        self.key = key
        self.label = label
        self.level = level
        self.width = 0
        self.height = 0

    def wrap(self, *_args: object) -> tuple[int, int]:
        return 0, 0

    def draw(self) -> None:
        self.canv.bookmarkPage(self.key)
        self.canv.addOutlineEntry(self.label, self.key, level=self.level, closed=False)


def _fit_image(image_path: str, max_w: float, max_h: float) -> Image:
    with PILImage.open(image_path) as pil_img:
        orig_w, orig_h = pil_img.size
    scale = min(max_w / orig_w, max_h / orig_h, 1.0)
    return Image(image_path, width=orig_w * scale, height=orig_h * scale)


def _add_paragraphs(story_flow: list, text: str, body_style: ParagraphStyle) -> None:
    for paragraph in text.split("\n\n"):
        paragraph = paragraph.strip()
        if paragraph:
            story_flow.append(Paragraph(to_pdf(paragraph.replace("\n", " ")), body_style))


def _render_illustration(
    story_flow: list,
    illustration: IllustrationSpec,
    styles: dict[str, ParagraphStyle],
) -> None:
    if not illustration.image_path:
        return
    image_path = Path(illustration.image_path)
    if not image_path.exists():
        logger.warning(f"PDF: illustration missing on disk: {image_path}")
        return

    cfg = config.pdf
    img = _fit_image(str(image_path), cfg.image_max_width, cfg.image_max_height)
    if illustration.placement == "full_page":
        story_flow.append(PageBreak())
        story_flow.append(Spacer(1, 24))
    story_flow.append(img)
    if illustration.caption:
        story_flow.append(Paragraph(to_pdf(illustration.caption), styles["caption"]))
    if illustration.placement == "full_page":
        story_flow.append(PageBreak())


def _render_chapter(
    story_flow: list,
    chapter: Chapter,
    styles: dict[str, ParagraphStyle],
) -> None:
    story_flow.append(PageBreak())
    story_flow.append(
        _OutlineEntry(
            key=f"chapter_{chapter.number}",
            label=f"Chapter {chapter.number}: {chapter.title}",
            level=0,
        )
    )
    story_flow.append(Paragraph(f"Chapter {chapter.number}", styles["chapter"]))
    story_flow.append(Paragraph(chapter.title, styles["chapter"]))
    story_flow.append(Spacer(1, 12))

    inline_illustrations = [ill for ill in chapter.illustrations if ill.placement != "full_page"]
    full_page_illustrations = [ill for ill in chapter.illustrations if ill.placement == "full_page"]

    if full_page_illustrations:
        _render_illustration(story_flow, full_page_illustrations[0], styles)
        remaining_full_page = full_page_illustrations[1:]
    else:
        remaining_full_page = []

    _add_paragraphs(story_flow, chapter.text, styles["body"])

    for illustration in inline_illustrations:
        _render_illustration(story_flow, illustration, styles)

    for illustration in remaining_full_page:
        _render_illustration(story_flow, illustration, styles)

    if chapter.poem:
        _render_poem(story_flow, chapter.poem, styles)

    if chapter.reflection is not None:
        _render_reflection(story_flow, chapter.reflection.questions, styles)


def _render_poem(
    story_flow: list,
    poem_text: str,
    styles: dict[str, ParagraphStyle],
) -> None:
    """Render the chapter's poem set off from prose with ornament dividers.

    Layout: hairline → fleuron divider → verse lines → fleuron divider → hairline.
    The whole block is wrapped in `KeepTogether` so the poem never splits across
    two pages — if it can't fit at the current position, it's pushed to a fresh
    page in one piece.
    """
    story_flow.append(Spacer(1, 24))
    poem_block: list = [
        HRFlowable(
            width="40%",
            thickness=0.5,
            color=HexColor("#D5C8E4"),
            spaceBefore=0,
            spaceAfter=0,
            hAlign="CENTER",
        ),
        # Fleuron + dashes: an old typographer's mark of verse.
        Paragraph("─── ❦ ───", styles["poem_ornament"]),
    ]

    for line in poem_text.split("\n"):
        line = line.rstrip()
        # An empty line inside a poem is a stanza break — render as a small gap.
        if not line:
            poem_block.append(Spacer(1, 8))
            continue
        poem_block.append(Paragraph(to_pdf(line), styles["poem"]))

    poem_block.extend(
        [
            Paragraph("─── ❦ ───", styles["poem_ornament"]),
            HRFlowable(
                width="40%",
                thickness=0.5,
                color=HexColor("#D5C8E4"),
                spaceBefore=0,
                spaceAfter=0,
                hAlign="CENTER",
            ),
        ]
    )
    story_flow.append(KeepTogether(poem_block))
    story_flow.append(Spacer(1, 24))


def _render_reflection(
    story_flow: list,
    questions: list[str],
    styles: dict[str, ParagraphStyle],
) -> None:
    """Reflection questions on their own page so they read as a deliberate pause."""
    story_flow.append(PageBreak())
    story_flow.append(Paragraph("Think About It", styles["chapter"]))
    story_flow.append(Spacer(1, 18))
    for i, question in enumerate(questions, 1):
        story_flow.append(Paragraph(f"{i}. {to_pdf(question)}", styles["list_item"]))
        story_flow.append(Spacer(1, 8))


def _render_experiment(
    story_flow: list,
    experiment: Experiment,
    styles: dict[str, ParagraphStyle],
) -> None:
    story_flow.append(PageBreak())
    story_flow.append(_OutlineEntry(key="experiment", label="Try This at Home", level=0))
    story_flow.append(Paragraph("Try This at Home", styles["chapter"]))
    story_flow.append(Paragraph(experiment.title, styles["chapter"]))
    story_flow.append(Spacer(1, 12))

    story_flow.append(Paragraph(f"<i>{to_pdf(experiment.concept)}</i>", styles["body"]))

    story_flow.append(Paragraph("You will need", styles["section_heading"]))
    for material in experiment.materials:
        story_flow.append(Paragraph(f"• {to_pdf(material)}", styles["list_item"]))

    story_flow.append(Paragraph("Steps", styles["section_heading"]))
    for i, step in enumerate(experiment.steps, 1):
        story_flow.append(Paragraph(f"{i}. {to_pdf(step)}", styles["list_item"]))

    story_flow.append(Paragraph("What to look for", styles["section_heading"]))
    story_flow.append(Paragraph(to_pdf(experiment.what_to_observe), styles["body"]))

    if experiment.safety_note:
        story_flow.append(Paragraph("Safety", styles["section_heading"]))
        story_flow.append(Paragraph(to_pdf(experiment.safety_note), styles["body"]))


def _render_biography(
    story_flow: list,
    biography: Biography,
    styles: dict[str, ParagraphStyle],
) -> None:
    story_flow.append(PageBreak())
    story_flow.append(_OutlineEntry(key="biography", label=f"Meet {biography.name}", level=0))
    story_flow.append(Paragraph(f"Meet {biography.name}", styles["chapter"]))
    subtitle = biography.title
    if biography.lifespan:
        subtitle = f"{biography.title} · {biography.lifespan}"
    story_flow.append(Paragraph(subtitle, styles["meta"]))
    story_flow.append(Spacer(1, 12))

    story_flow.append(Paragraph(f"<i>{to_pdf(biography.one_line)}</i>", styles["body"]))
    story_flow.append(Spacer(1, 6))
    _add_paragraphs(story_flow, biography.summary, styles["body"])

    story_flow.append(Paragraph("Fun facts", styles["section_heading"]))
    for fact in biography.fun_facts:
        story_flow.append(Paragraph(f"• {to_pdf(fact)}", styles["list_item"]))

    story_flow.append(Paragraph("Why this matters", styles["section_heading"]))
    story_flow.append(Paragraph(to_pdf(biography.why_inspiring), styles["body"]))


def _build_front_matter(
    story_flow: list,
    book: BookContent,
    styles: dict[str, ParagraphStyle],
) -> None:
    metadata = book.metadata
    story_flow.append(Spacer(1, 80))
    story_flow.append(Paragraph(metadata.title, styles["title"]))
    if metadata.subtitle:
        story_flow.append(Paragraph(f"<i>{metadata.subtitle}</i>", styles["meta"]))
    if metadata.series:
        series_line = metadata.series + (f", Volume {metadata.volume}" if metadata.volume else "")
        story_flow.append(Paragraph(series_line, styles["meta"]))
    if metadata.tagline:
        story_flow.append(Spacer(1, 24))
        story_flow.append(Paragraph(f'"{metadata.tagline}"', styles["meta"]))
    story_flow.append(Spacer(1, 60))
    story_flow.append(Paragraph(f"by {metadata.author}", styles["meta"]))
    story_flow.append(Spacer(1, 40))
    story_flow.append(Paragraph(config.book.publisher, styles["meta"]))
    story_flow.append(Paragraph(config.book.publisher_location, styles["meta"]))
    story_flow.append(PageBreak())

    story_flow.append(Spacer(1, 120))
    copyright_line = f"© {config.book.publication_year} {metadata.author}. All rights reserved."
    story_flow.append(Paragraph(copyright_line, styles["meta"]))
    story_flow.append(Paragraph(config.book.edition, styles["meta"]))
    if config.book.isbn_pdf:
        story_flow.append(Paragraph(f"ISBN (PDF): {config.book.isbn_pdf}", styles["meta"]))
    story_flow.append(PageBreak())

    if metadata.dedication_text:
        story_flow.append(Spacer(1, 180))
        story_flow.append(Paragraph(f"<i>{metadata.dedication_text}</i>", styles["meta"]))
        story_flow.append(PageBreak())

    story_flow.append(_OutlineEntry(key="contents", label="Contents", level=0))
    story_flow.append(Paragraph("Contents", styles["chapter"]))
    story_flow.append(Spacer(1, 18))
    for entry, page_label, anchor in _toc_entries(book):
        # `<link href="#anchor">` makes the entry clickable; the same anchor is
        # registered as a bookmark/outline entry where the section starts.
        toc_line = (
            f'<link href="#{anchor}" color="#1565C0">{entry}</link>'
            f"<font color='#9E8AB0'> &#8230; </font>{page_label}"
        )
        story_flow.append(Paragraph(toc_line, styles["toc_entry"]))


def _render_for_parents(
    story_flow: list,
    text: str,
    styles: dict[str, ParagraphStyle],
) -> None:
    story_flow.append(PageBreak())
    story_flow.append(_OutlineEntry(key="for_parents", label="For Parents & Educators", level=0))
    story_flow.append(Paragraph("For Parents & Educators", styles["chapter"]))
    story_flow.append(Spacer(1, 12))
    _add_paragraphs(story_flow, text, styles["body"])


def _toc_entries(book: BookContent) -> list[tuple[str, str, str]]:
    """Build `(label, page-number, anchor)` tuples for the ToC.

    The anchor is the bookmark key registered by `_OutlineEntry` at the section
    start — used by both the in-page ToC link and the PDF outline pane.
    """
    entries: list[tuple[str, str, str]] = []
    for chapter in book.chapters:
        entries.append(
            (
                f"Chapter {chapter.number}: {chapter.title}",
                str(chapter.page_start),
                f"chapter_{chapter.number}",
            )
        )
    if book.experiment is not None:
        entries.append(("Try This at Home", "see end", "experiment"))
    if book.biography is not None:
        entries.append((f"Meet {book.biography.name}", "see end", "biography"))
    if book.back_matter_for_parents:
        entries.append(("For Parents & Educators", "see end", "for_parents"))
    return entries


def _build_page_templates(cfg: object) -> tuple[PageTemplate, PageTemplate]:
    """Build (cover, body) page templates.

    Cover template uses a zero-padding frame so the cover image fills the page
    edge-to-edge ('full bleed'). Body template uses the configured margins.
    """
    page_w, page_h = cfg.page_size
    cover_frame = Frame(
        0,
        0,
        page_w,
        page_h,
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
        id="cover_frame",
        showBoundary=0,
    )
    body_frame = Frame(
        cfg.margin,
        cfg.margin,
        page_w - 2 * cfg.margin,
        page_h - 2 * cfg.margin,
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
        id="body_frame",
        showBoundary=0,
    )
    return PageTemplate(id="cover", frames=[cover_frame]), PageTemplate(
        id="body", frames=[body_frame]
    )


def generate_pdf(book: BookContent, output_path: Path) -> Path:
    """Render the book to a PDF file, including front + back covers when present."""
    logger.info(f"PDFGenerator: writing {output_path}")
    cfg = config.pdf
    styles = _build_styles()
    page_w, page_h = cfg.page_size

    cover_template, body_template = _build_page_templates(cfg)
    has_cover = book.cover is not None
    # When the book has a cover, start on the cover template so the first page
    # is the full-bleed front cover; otherwise start on body.
    templates = [cover_template, body_template] if has_cover else [body_template, cover_template]

    doc = BaseDocTemplate(
        str(output_path),
        pagesize=cfg.page_size,
        pageTemplates=templates,
        title=book.metadata.title,
        author=book.metadata.author,
    )

    story_flow: list = []
    if has_cover:
        front = Image(book.cover.front_path, width=page_w, height=page_h)
        story_flow.append(front)
        story_flow.append(NextPageTemplate("body"))
        story_flow.append(PageBreak())

    _build_front_matter(story_flow, book, styles)
    for chapter in book.chapters:
        _render_chapter(story_flow, chapter, styles)

    if book.experiment is not None:
        _render_experiment(story_flow, book.experiment, styles)

    if book.biography is not None:
        _render_biography(story_flow, book.biography, styles)

    if book.back_matter_for_parents:
        _render_for_parents(story_flow, book.back_matter_for_parents, styles)

    if has_cover:
        story_flow.append(NextPageTemplate("cover"))
        story_flow.append(PageBreak())
        back = Image(book.cover.back_path, width=page_w, height=page_h)
        story_flow.append(back)

    doc.build(story_flow)
    logger.info(f"PDFGenerator: done ({output_path.stat().st_size // 1024}KB)")
    return output_path

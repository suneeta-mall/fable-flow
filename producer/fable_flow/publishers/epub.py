"""Render BookContent to a reflowable EPUB 3.0 file."""

from __future__ import annotations

import shutil
import tempfile
import uuid
import zipfile
from datetime import UTC, datetime, timezone
from html import escape
from pathlib import Path

from loguru import logger

from fable_flow.config import config
from fable_flow.schemas.book_content import (
    Biography,
    BookContent,
    Chapter,
    Experiment,
    IllustrationSpec,
)

CSS = """\
body { font-family: Georgia, serif; line-height: 1.5; margin: 1.2em; color: #212121; }
h1.book-title { color: #1565C0; text-align: center; font-size: 2.2em; margin-top: 3em; }
h2.chapter-title { color: #2E7D32; text-align: center; margin-top: 2em; font-size: 1.6em; }
h3.chapter-number { color: #2E7D32; text-align: center; font-size: 1.1em; margin: 0; }
.front-matter { text-align: center; margin-top: 3em; }
.front-matter p { margin: 0.4em 0; }
.copyright { font-size: 0.85em; color: #555; }

/* Table of contents (visible page). */
.toc { margin: 2em 1.5em; }
.toc h2 { color: #2E7D32; text-align: center; margin-bottom: 1.5em; }
.toc ol { list-style: none; padding-left: 0; }
.toc li { margin: 0.5em 0; }
.toc li a { text-decoration: none; color: #212121; }
.toc li.toc-back-matter { margin-top: 1em; font-style: italic; color: #5D4E75; }

p.body { text-indent: 1.5em; margin: 0 0 0.6em 0; text-align: justify; }

.illustration { text-align: center; margin: 1.5em 0; page-break-inside: avoid; }
.illustration img { max-width: 100%; height: auto; }
.illustration .caption { font-style: italic; color: #5D4E75; font-size: 0.9em; margin-top: 0.4em; }
.full-page-illustration { page-break-before: always; text-align: center; }

/* "Think About It" reflection page — starts on a new page per the editorial pattern. */
.reflection { page-break-before: always; margin: 2em 1.5em; }
.reflection h2 { color: #2E7D32; text-align: center; margin-bottom: 1.5em; font-size: 1.5em; }
.reflection ol { padding-left: 1.6em; }
.reflection li { margin-bottom: 1em; line-height: 1.6; }

/* Thematic poem — set off as verse with serif italic, ornament dividers, and a soft card. */
.poem {
  text-align: center;
  font-style: italic;
  color: #4A3F60;
  margin: 2.5em 3em;
  padding: 1.6em 1.8em;
  line-height: 1.8;
  font-size: 1.05em;
  background: #FAF7FC;
  border-top: 1px solid #D5C8E4;
  border-bottom: 1px solid #D5C8E4;
  page-break-inside: avoid;
  break-inside: avoid;
}
.poem-ornament {
  color: #B6A4CD;
  letter-spacing: 0.4em;
  font-style: normal;
  margin: 0.2em 0 1.1em 0;
}
.poem-ornament-bottom { margin: 1.1em 0 0.2em 0; }
.poem-line { margin: 0; }
.poem-stanza-break { height: 0.7em; margin: 0; }

.dedication { text-align: center; margin: 6em 2em; font-size: 1.1em; color: #5D4E75; }
.front-matter .subtitle { font-style: italic; margin-top: -0.4em; }
.front-matter .tagline { margin-top: 1.4em; font-style: italic; color: #555; }

.for-parents { margin: 1em 1.5em; }
.for-parents h2 { color: #2E7D32; }

/* Back-matter pages each start on a new page. */
.experiment, .biography, .for-parents { page-break-before: always; }
.experiment h2, .biography h2 { color: #2E7D32; margin-top: 1.5em; }
.experiment h3, .biography h3 { color: #2E7D32; margin-top: 1.2em; font-size: 1.1em; }
.experiment .concept, .biography .one-line { font-style: italic; color: #5D4E75; margin: 0.6em 0 1em 0; }
.experiment ul, .experiment ol, .biography ul { padding-left: 1.6em; }
.experiment li, .biography li { margin-bottom: 0.4em; }
.biography .subtitle { text-align: center; color: #555; margin: 0 0 1em 0; }
.experiment .safety { background: #FFF7E6; border-left: 4px solid #BF360C; padding: 0.6em 1em; margin-top: 1em; }

/* Full-bleed front and back cover pages. */
.cover-page { margin: 0; padding: 0; text-align: center; page-break-after: always; }
.cover-page img { max-width: 100%; max-height: 100vh; height: auto; display: block; margin: 0 auto; }
.back-cover-page { margin: 0; padding: 0; text-align: center; page-break-before: always; }
.back-cover-page img { max-width: 100%; max-height: 100vh; height: auto; display: block; margin: 0 auto; }
"""

CONTAINER_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""


def _chapter_html(chapter: Chapter, image_assets: dict[str, str]) -> str:
    parts: list[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        "<!DOCTYPE html>",
        '<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">',
        "<head>",
        f"  <title>Chapter {chapter.number}: {escape(chapter.title)}</title>",
        '  <link rel="stylesheet" type="text/css" href="style.css"/>',
        "</head>",
        "<body>",
        f'<h3 class="chapter-number">Chapter {chapter.number}</h3>',
        f'<h2 class="chapter-title">{escape(chapter.title)}</h2>',
    ]

    inline = [ill for ill in chapter.illustrations if ill.placement != "full_page"]
    full_page = [ill for ill in chapter.illustrations if ill.placement == "full_page"]

    for ill in full_page:
        parts.append(_illustration_html(ill, image_assets, full_page=True))

    paragraphs = [p.strip() for p in chapter.text.split("\n\n") if p.strip()]
    inline_iter = iter(inline)
    inline_after = max(1, len(paragraphs) // max(1, len(inline) + 1)) if inline else 0
    for idx, paragraph in enumerate(paragraphs, 1):
        parts.append(f'<p class="body">{escape(paragraph)}</p>')
        if inline_after and idx % inline_after == 0:
            next_ill = next(inline_iter, None)
            if next_ill is not None:
                parts.append(_illustration_html(next_ill, image_assets, full_page=False))

    for leftover in inline_iter:
        parts.append(_illustration_html(leftover, image_assets, full_page=False))

    if chapter.poem:
        parts.append(_poem_html(chapter.poem))

    if chapter.reflection is not None:
        parts.append(_reflection_html(chapter.reflection.questions))

    parts.extend(["</body>", "</html>"])
    return "\n".join(parts)


def _poem_html(poem_text: str) -> str:
    """Render the chapter's thematic poem with ornament dividers and soft card.

    Layout: top ornament → verse lines → bottom ornament, wrapped in a `.poem`
    block with subtle background and rules. CSS lives in CSS module above.
    """
    lines_html = []
    for line in poem_text.split("\n"):
        line = line.rstrip()
        if not line:
            lines_html.append('<p class="poem-stanza-break"></p>')
        else:
            lines_html.append(f'<p class="poem-line">{escape(line)}</p>')
    body = "\n".join(lines_html)
    return (
        '<div class="poem">'
        '<p class="poem-ornament">─── ❦ ───</p>'
        f"{body}"
        '<p class="poem-ornament poem-ornament-bottom">─── ❦ ───</p>'
        "</div>"
    )


def _reflection_html(questions: list[str]) -> str:
    """Render reflection block — `.reflection` CSS forces a page break before it."""
    items = "\n".join(f"    <li>{escape(q)}</li>" for q in questions)
    return f'<div class="reflection"><h2>Think About It</h2><ol>\n{items}\n</ol></div>'


def _experiment_html(experiment: Experiment) -> str:
    materials = "\n".join(f"    <li>{escape(m)}</li>" for m in experiment.materials)
    steps = "\n".join(f"    <li>{escape(s)}</li>" for s in experiment.steps)
    safety = (
        f'<div class="safety"><strong>Safety:</strong> {escape(experiment.safety_note)}</div>'
        if experiment.safety_note
        else ""
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">
<head>
  <title>Try This at Home</title>
  <link rel="stylesheet" type="text/css" href="style.css"/>
</head>
<body>
<div class="experiment">
<h2>Try This at Home</h2>
<h3>{escape(experiment.title)}</h3>
<p class="concept">{escape(experiment.concept)}</p>

<h3>You will need</h3>
<ul>
{materials}
</ul>

<h3>Steps</h3>
<ol>
{steps}
</ol>

<h3>What to look for</h3>
<p>{escape(experiment.what_to_observe)}</p>

{safety}
</div>
</body>
</html>"""


def _biography_html(biography: Biography) -> str:
    fun_facts = "\n".join(f"    <li>{escape(f)}</li>" for f in biography.fun_facts)
    subtitle = biography.title
    if biography.lifespan:
        subtitle = f"{biography.title} · {biography.lifespan}"
    summary_paragraphs = "\n".join(
        f"<p>{escape(p.strip())}</p>" for p in biography.summary.split("\n\n") if p.strip()
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">
<head>
  <title>Meet {escape(biography.name)}</title>
  <link rel="stylesheet" type="text/css" href="style.css"/>
</head>
<body>
<div class="biography">
<h2>Meet {escape(biography.name)}</h2>
<p class="subtitle">{escape(subtitle)}</p>
<p class="one-line">{escape(biography.one_line)}</p>

{summary_paragraphs}

<h3>Fun facts</h3>
<ul>
{fun_facts}
</ul>

<h3>Why this matters</h3>
<p>{escape(biography.why_inspiring)}</p>
</div>
</body>
</html>"""


def _illustration_html(ill: IllustrationSpec, image_assets: dict[str, str], full_page: bool) -> str:
    if not ill.image_path or ill.image_path not in image_assets:
        return ""
    href = image_assets[ill.image_path]
    css_class = "full-page-illustration" if full_page else "illustration"
    # `description` is the image-gen prompt — never user-facing. Caption is the
    # editorial line shown to the reader; alt text falls back to it for a11y.
    alt = escape(ill.caption or ill.scene_context)
    caption_html = f'<div class="caption">{escape(ill.caption)}</div>' if ill.caption else ""
    return f'<div class="{css_class}"><img src="{href}" alt="{alt}"/>{caption_html}</div>'


def _front_matter_html(book: BookContent) -> str:
    metadata = book.metadata
    parts: list[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        "<!DOCTYPE html>",
        '<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">',
        "<head>",
        f"  <title>{escape(metadata.title)}</title>",
        '  <link rel="stylesheet" type="text/css" href="style.css"/>',
        "</head>",
        "<body>",
        f'<h1 class="book-title">{escape(metadata.title)}</h1>',
        '<div class="front-matter">',
    ]
    if metadata.subtitle:
        parts.append(f'<p class="subtitle"><em>{escape(metadata.subtitle)}</em></p>')
    if metadata.series:
        series_line = metadata.series + (f", Volume {metadata.volume}" if metadata.volume else "")
        parts.append(f"<p>{escape(series_line)}</p>")
    if metadata.tagline:
        parts.append(f'<p class="tagline">"{escape(metadata.tagline)}"</p>')
    parts.append(f"<p>by {escape(metadata.author)}</p>")
    parts.append(f"<p>{escape(config.book.publisher)}</p>")
    parts.append(f"<p>{escape(config.book.publisher_location)}</p>")
    parts.append('<p class="copyright">')
    parts.append(
        f"© {config.book.publication_year} {escape(metadata.author)}. All rights reserved."
    )
    parts.append("</p>")
    if config.book.isbn_epub:
        parts.append(f'<p class="copyright">ISBN (EPUB): {escape(config.book.isbn_epub)}</p>')
    parts.append("</div>")
    parts.extend(["</body>", "</html>"])
    return "\n".join(parts)


def _dedication_html(text: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">
<head>
  <title>Dedication</title>
  <link rel="stylesheet" type="text/css" href="style.css"/>
</head>
<body>
<div class="dedication"><em>{escape(text)}</em></div>
</body>
</html>"""


def _cover_html(image_href: str, title: str, css_class: str) -> str:
    """Wrap a cover image in a minimal full-page XHTML doc.

    `css_class` switches between front / back styling but both render full-bleed.
    """
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">
<head>
  <title>{escape(title)}</title>
  <link rel="stylesheet" type="text/css" href="style.css"/>
</head>
<body class="{css_class}">
<img src="{image_href}" alt="{escape(title)}"/>
</body>
</html>"""


def _for_parents_html(text: str) -> str:
    paragraphs = "\n".join(f"<p>{escape(p.strip())}</p>" for p in text.split("\n\n") if p.strip())
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">
<head>
  <title>For Parents &amp; Educators</title>
  <link rel="stylesheet" type="text/css" href="style.css"/>
</head>
<body>
<div class="for-parents">
<h2>For Parents &amp; Educators</h2>
{paragraphs}
</div>
</body>
</html>"""


def _toc_entries(book: BookContent) -> list[tuple[str, str, bool]]:
    """Return `(label, href, is_back_matter)` for every linkable section."""
    out: list[tuple[str, str, bool]] = []
    for ch in book.chapters:
        out.append((f"Chapter {ch.number}: {ch.title}", f"chapter_{ch.number}.xhtml", False))
    if book.experiment is not None:
        out.append(("Try This at Home", "experiment.xhtml", True))
    if book.biography is not None:
        out.append((f"Meet {book.biography.name}", "biography.xhtml", True))
    if book.back_matter_for_parents:
        out.append(("For Parents & Educators", "for_parents.xhtml", True))
    return out


def _toc_html(book: BookContent) -> str:
    """Visible Contents page — chapters then a back-matter group."""
    items_html = []
    for label, href, is_back_matter in _toc_entries(book):
        cls = ' class="toc-back-matter"' if is_back_matter else ""
        items_html.append(f'  <li{cls}><a href="{href}">{escape(label)}</a></li>')
    items = "\n".join(items_html)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">
<head>
  <title>Contents</title>
  <link rel="stylesheet" type="text/css" href="style.css"/>
</head>
<body>
<div class="toc">
<h2>Contents</h2>
<ol>
{items}
</ol>
</div>
</body>
</html>"""


def _nav_html(book: BookContent) -> str:
    """EPUB structural ToC — used by reader apps' nav drawer."""
    items_html = []
    for label, href, _is_back_matter in _toc_entries(book):
        items_html.append(f'      <li><a href="{href}">{escape(label)}</a></li>')
    items = "\n".join(items_html)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="en">
<head>
  <title>Contents</title>
  <link rel="stylesheet" type="text/css" href="style.css"/>
</head>
<body>
<nav epub:type="toc" id="toc">
  <h2>Contents</h2>
  <ol>
      <li><a href="front_matter.xhtml">Title Page</a></li>
      <li><a href="toc.xhtml">Contents</a></li>
{items}
  </ol>
</nav>
</body>
</html>"""


def _opf(book: BookContent, image_assets: dict[str, str], book_uuid: str) -> str:
    metadata = book.metadata
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    manifest_items = [
        '    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
        '    <item id="style" href="style.css" media-type="text/css"/>',
    ]
    spine_items: list[str] = []

    if book.cover is not None:
        # `properties="cover-image"` is the EPUB 3 cue that makes reader apps
        # display this image as the book's cover thumbnail / first page.
        manifest_items.append(
            '    <item id="cover-img" href="images/cover_front.png" '
            'media-type="image/png" properties="cover-image"/>'
        )
        manifest_items.append(
            '    <item id="cover-back-img" href="images/cover_back.png" media-type="image/png"/>'
        )
        manifest_items.append(
            '    <item id="cover" href="cover.xhtml" media-type="application/xhtml+xml"/>'
        )
        spine_items.append('    <itemref idref="cover"/>')

    manifest_items.extend(
        [
            '    <item id="front" href="front_matter.xhtml" media-type="application/xhtml+xml"/>',
            '    <item id="toc" href="toc.xhtml" media-type="application/xhtml+xml"/>',
        ]
    )
    spine_items.extend(
        [
            '    <itemref idref="front"/>',
            '    <itemref idref="toc"/>',
        ]
    )
    for chapter in book.chapters:
        manifest_items.append(
            f'    <item id="ch{chapter.number}" href="chapter_{chapter.number}.xhtml" '
            'media-type="application/xhtml+xml"/>'
        )
        spine_items.append(f'    <itemref idref="ch{chapter.number}"/>')

    if book.experiment is not None:
        manifest_items.append(
            '    <item id="experiment" href="experiment.xhtml" media-type="application/xhtml+xml"/>'
        )
        spine_items.append('    <itemref idref="experiment"/>')

    if book.biography is not None:
        manifest_items.append(
            '    <item id="biography" href="biography.xhtml" media-type="application/xhtml+xml"/>'
        )
        spine_items.append('    <itemref idref="biography"/>')

    if book.back_matter_for_parents:
        manifest_items.append(
            '    <item id="for_parents" href="for_parents.xhtml" media-type="application/xhtml+xml"/>'
        )
        spine_items.append('    <itemref idref="for_parents"/>')

    if book.cover is not None:
        manifest_items.append(
            '    <item id="back_cover" href="back_cover.xhtml" media-type="application/xhtml+xml"/>'
        )
        spine_items.append('    <itemref idref="back_cover"/>')

    if book.metadata.dedication_text:
        manifest_items.append(
            '    <item id="dedication" href="dedication.xhtml" media-type="application/xhtml+xml"/>'
        )
        front_idx = spine_items.index('    <itemref idref="front"/>')
        spine_items.insert(front_idx + 1, '    <itemref idref="dedication"/>')

    for idx, (_, href) in enumerate(image_assets.items()):
        manifest_items.append(f'    <item id="img{idx}" href="{href}" media-type="image/png"/>')

    identifier = config.book.isbn_epub or f"urn:uuid:{book_uuid}"
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<package version="3.0" xmlns="http://www.idpf.org/2007/opf" unique-identifier="bookid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="bookid">{escape(identifier)}</dc:identifier>
    <dc:title>{escape(metadata.title)}</dc:title>
    <dc:creator>{escape(metadata.author)}</dc:creator>
    <dc:publisher>{escape(config.book.publisher)}</dc:publisher>
    <dc:language>en</dc:language>
    <dc:date>{config.book.publication_year}-01-01</dc:date>
    <meta property="dcterms:modified">{now}</meta>
  </metadata>
  <manifest>
{chr(10).join(manifest_items)}
  </manifest>
  <spine>
{chr(10).join(spine_items)}
  </spine>
</package>
"""


def _collect_images(book: BookContent) -> dict[str, str]:
    """Map absolute source path -> EPUB relative href ('images/foo.png')."""
    out: dict[str, str] = {}
    for chapter in book.chapters:
        for illustration in chapter.illustrations:
            if illustration.image_path and illustration.image_path not in out:
                src = Path(illustration.image_path)
                if src.exists():
                    out[illustration.image_path] = f"images/{src.name}"
                else:
                    logger.warning(f"EPUB: illustration missing on disk: {src}")
    return out


def generate_epub(book: BookContent, output_path: Path) -> Path:
    """Render the book to an EPUB file."""
    logger.info(f"EPUBGenerator: writing {output_path}")
    book_uuid = str(uuid.uuid4())
    image_assets = _collect_images(book)

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "META-INF").mkdir()
        oebps = root / "OEBPS"
        oebps.mkdir()
        (oebps / "images").mkdir()

        (root / "mimetype").write_text("application/epub+zip", encoding="utf-8")
        (root / "META-INF" / "container.xml").write_text(CONTAINER_XML, encoding="utf-8")
        (oebps / "style.css").write_text(CSS, encoding="utf-8")
        if book.cover is not None:
            shutil.copy(book.cover.front_path, oebps / "images" / "cover_front.png")
            shutil.copy(book.cover.back_path, oebps / "images" / "cover_back.png")
            (oebps / "cover.xhtml").write_text(
                _cover_html("images/cover_front.png", "Cover", "cover-page"),
                encoding="utf-8",
            )
            (oebps / "back_cover.xhtml").write_text(
                _cover_html("images/cover_back.png", "Back Cover", "back-cover-page"),
                encoding="utf-8",
            )
        (oebps / "front_matter.xhtml").write_text(_front_matter_html(book), encoding="utf-8")
        (oebps / "toc.xhtml").write_text(_toc_html(book), encoding="utf-8")
        (oebps / "nav.xhtml").write_text(_nav_html(book), encoding="utf-8")
        for chapter in book.chapters:
            (oebps / f"chapter_{chapter.number}.xhtml").write_text(
                _chapter_html(chapter, image_assets), encoding="utf-8"
            )
        if book.metadata.dedication_text:
            (oebps / "dedication.xhtml").write_text(
                _dedication_html(book.metadata.dedication_text), encoding="utf-8"
            )
        if book.experiment is not None:
            (oebps / "experiment.xhtml").write_text(
                _experiment_html(book.experiment), encoding="utf-8"
            )
        if book.biography is not None:
            (oebps / "biography.xhtml").write_text(
                _biography_html(book.biography), encoding="utf-8"
            )
        if book.back_matter_for_parents:
            (oebps / "for_parents.xhtml").write_text(
                _for_parents_html(book.back_matter_for_parents), encoding="utf-8"
            )

        for src_path, href in image_assets.items():
            shutil.copy(src_path, oebps / href)

        (oebps / "content.opf").write_text(_opf(book, image_assets, book_uuid), encoding="utf-8")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(root / "mimetype", "mimetype", compress_type=zipfile.ZIP_STORED)
            for path in root.rglob("*"):
                if path.is_file() and path.name != "mimetype":
                    zf.write(path, path.relative_to(root))

    logger.info(f"EPUBGenerator: done ({output_path.stat().st_size // 1024}KB)")
    return output_path

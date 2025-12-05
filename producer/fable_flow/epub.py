import re
import uuid
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup
from loguru import logger
from PIL import Image, ImageDraw, ImageFont

from fable_flow.book_structure import BookStructureGenerator
from fable_flow.book_utils import BookContentProcessor
from fable_flow.common import Manuscript
from fable_flow.config import config

_LOGO_PATH = Path(__file__).parent.parent.parent / "docs" / "assets" / "logo_horizontal.png"


class EPUBGenerator:
    """Generate EPUB files from HTML content and book metadata."""

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self._image_reference_map: dict[str, Any] = {}

    def _is_descendant_of_book(self, child, book_div):
        """Check if child element is a descendant of book div."""
        if not child or not book_div:
            return False
        current = child.parent
        while current:
            if current == book_div:
                return True
            current = current.parent
        return False

    def generate_epub(
        self, html_content: str, message: Manuscript, output_path: Path, book_metadata: dict
    ) -> None:
        """Generate an EPUB file from HTML content with metadata."""
        logger.info(f"EPUBGenerator: Generating EPUB from HTML with {len(html_content)} characters")

        # Clean HTML content using shared utility
        html_content = BookContentProcessor.clean_html_content(html_content)

        # Parse HTML structure
        soup = BeautifulSoup(html_content, "html.parser")
        book_div = soup.find("div", class_="book")

        # Extract title and subtitle from HTML
        title_elem = soup.find(class_="front-cover-title")
        subtitle_elem = soup.find(class_="front-cover-subtitle")

        if title_elem:
            book_metadata["title"] = title_elem.get_text().strip()
        if subtitle_elem:
            book_metadata["subtitle"] = subtitle_elem.get_text().strip()

        # Validate and clean metadata
        book_metadata = BookContentProcessor.validate_book_metadata(book_metadata)

        # Collect all content elements - front matter + book content
        all_elements = []

        # First collect front matter elements (outside book div)
        if book_div:
            for elem in soup.find_all("div", class_="page-spread"):
                if elem != book_div and not self._is_descendant_of_book(elem, book_div):
                    all_elements.append(elem)

        if not book_div:
            logger.warning("EPUBGenerator: No book div found, processing all page-spread elements")
            all_elements = soup.find_all("div", class_="page-spread")
        else:
            # Then add book content elements
            all_elements.extend(book_div.find_all("div", class_="page-spread"))

        # Extract book metadata
        title = book_metadata.get("title", "FableFlow Book")
        author = book_metadata.get("author", "FableFlow")
        publisher = book_metadata.get("publisher", "FableFlow Publishing")

        # Create EPUB structure
        epub_id = str(uuid.uuid4())
        creation_date = datetime.now().isoformat()

        try:
            # Create EPUB cover with text overlay for bookshelf display
            self._create_epub_cover_with_text(book_metadata)

            image_files = self._collect_images()

            with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as epub_zip:
                # 1. Add mimetype (uncompressed)
                epub_zip.writestr(
                    "mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED
                )

                # 2. Add META-INF/container.xml
                container_xml = self._create_container_xml()
                epub_zip.writestr("META-INF/container.xml", container_xml)

                # 3. Add content.opf (package document)
                content_opf = self._create_content_opf(
                    title, author, publisher, epub_id, creation_date, image_files
                )
                epub_zip.writestr("OEBPS/content.opf", content_opf)

                # 4. Add toc.ncx (navigation)
                toc_ncx = self._create_toc_ncx(title, author, epub_id, soup)
                epub_zip.writestr("OEBPS/toc.ncx", toc_ncx)

                # 5. Add stylesheet
                css_content = self._create_epub_css()
                epub_zip.writestr("OEBPS/styles/main.css", css_content)

                # 6. Add HTML chapters
                self._add_html_chapters(epub_zip, soup, book_metadata)

                # 7. Add images with proper manifest references
                self._add_images_to_epub(epub_zip, image_files)

            logger.info(f"EPUBGenerator: EPUB generated successfully: {output_path}")

        except Exception as e:
            logger.error(f"EPUBGenerator: EPUB generation failed: {e}")
            self._create_fallback_epub(output_path, title, author, html_content)

    def _clean_html_content(self, html_content: str) -> str:
        """Clean HTML content by removing markdown code blocks."""
        # Remove markdown code block markers
        html_content = re.sub(r"^```html\s*\n?", "", html_content, flags=re.MULTILINE)
        html_content = re.sub(r"\n?```\s*$", "", html_content, flags=re.MULTILINE)
        html_content = re.sub(r"^```\s*\n?", "", html_content, flags=re.MULTILINE)

        # Remove any stray backticks
        html_content = html_content.strip("`")
        html_content = html_content.strip()

        logger.debug("EPUBGenerator: Cleaned HTML content")
        return html_content

    def _create_container_xml(self) -> str:
        """Create the META-INF/container.xml file."""
        return """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
    <rootfiles>
        <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
    </rootfiles>
</container>"""

    def _create_content_opf(
        self,
        title: str,
        author: str,
        publisher: str,
        epub_id: str,
        creation_date: str,
        image_files: list = None,
    ) -> str:
        """Create the OEBPS/content.opf package document.

        Uses EPUB 3.0 format with modern metadata and navigation.
        Includes both toc.ncx (backwards compatibility) and nav.xhtml (EPUB 3).
        """
        book_config = config.book
        isbn = book_config.isbn_epub if hasattr(config, "book") else "978-0-XXXXX-XXX-Y"

        return f"""<?xml version="1.0" encoding="UTF-8"?>
<package version="3.0" xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookId">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">
        <!-- Required metadata -->
        <dc:identifier id="BookId">{isbn}</dc:identifier>
        <dc:title>{title}</dc:title>
        <dc:language>en</dc:language>

        <!-- Additional metadata -->
        <dc:creator id="creator">{author}</dc:creator>
        <dc:publisher>{publisher}</dc:publisher>
        <dc:date>{creation_date[:10]}</dc:date>
        <dc:subject>Children's Literature</dc:subject>
        <dc:subject>Educational</dc:subject>
        <dc:subject>Science</dc:subject>
        <dc:description>An engaging educational children's book that combines storytelling with scientific learning.</dc:description>

        <!-- EPUB 3 metadata -->
        <meta property="dcterms:modified">{creation_date}</meta>
        <meta name="cover" content="cover-image"/>
    </metadata>

    <manifest>
        <!-- Navigation -->
        <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
        <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>

        <!-- Stylesheets -->
        <item id="css" href="styles/main.css" media-type="text/css"/>

        <!-- Content -->
        <item id="cover" href="cover.xhtml" media-type="application/xhtml+xml"/>
        <item id="title-page" href="title-page.xhtml" media-type="application/xhtml+xml"/>
        <item id="publication-info" href="publication-info.xhtml" media-type="application/xhtml+xml"/>
        <item id="toc-page" href="toc-page.xhtml" media-type="application/xhtml+xml"/>
        <item id="preface" href="preface.xhtml" media-type="application/xhtml+xml"/>
        <item id="content" href="content.xhtml" media-type="application/xhtml+xml"/>
        <item id="about" href="about.xhtml" media-type="application/xhtml+xml"/>
        <item id="index" href="index.xhtml" media-type="application/xhtml+xml"/>
        <item id="front-cover" href="front-cover.xhtml" media-type="application/xhtml+xml"/>
        <item id="back-cover" href="back-cover.xhtml" media-type="application/xhtml+xml"/>

        <!-- Images -->{self._generate_image_manifest_entries(image_files)}
    </manifest>

    <spine toc="ncx">
        <itemref idref="front-cover"/>
        <itemref idref="title-page"/>
        <itemref idref="publication-info"/>
        <itemref idref="toc-page"/>
        <itemref idref="preface"/>
        <itemref idref="content"/>
        <itemref idref="about"/>
        <itemref idref="index"/>
        <itemref idref="back-cover"/>
    </spine>

    <guide>
        <reference type="cover" title="Front Cover" href="front-cover.xhtml"/>
        <reference type="title-page" title="Title Page" href="title-page.xhtml"/>
        <reference type="toc" title="Table of Contents" href="toc-page.xhtml"/>
        <reference type="text" title="Content" href="content.xhtml"/>
    </guide>
</package>"""

    def _create_toc_ncx(self, title: str, author: str, epub_id: str, soup: BeautifulSoup) -> str:
        """Create the OEBPS/toc.ncx navigation file."""
        # Extract chapter titles from the HTML
        soup.find_all("h2", class_="chapter-title")

        nav_points = []
        play_order = 1

        # Add standard sections (Note: cover.xhtml is for EPUB readers, not TOC navigation)
        standard_sections = [
            ("front-cover", "Front Cover", "front-cover.xhtml"),
            ("title", "Title Page", "title-page.xhtml"),
            ("pub-info", "Publication Info", "publication-info.xhtml"),
            ("toc", "Contents", "toc-page.xhtml"),
            ("preface", "Preface", "preface.xhtml"),
        ]

        for section_id, section_title, section_href in standard_sections:
            nav_points.append(f"""
        <navPoint id="{section_id}" playOrder="{play_order}">
            <navLabel><text>{section_title}</text></navLabel>
            <content src="{section_href}"/>
        </navPoint>""")
            play_order += 1

        # Add story content
        nav_points.append(f"""
        <navPoint id="content" playOrder="{play_order}">
            <navLabel><text>Story</text></navLabel>
            <content src="content.xhtml"/>
        </navPoint>""")
        play_order += 1

        # Add back matter
        back_matter = [
            ("about", "About the Author", "about.xhtml"),
            ("index", "Index", "index.xhtml"),
        ]

        for section_id, section_title, section_href in back_matter:
            nav_points.append(f"""
        <navPoint id="{section_id}" playOrder="{play_order}">
            <navLabel><text>{section_title}</text></navLabel>
            <content src="{section_href}"/>
        </navPoint>""")
            play_order += 1

        nav_points_str = "".join(nav_points)

        return f"""<?xml version="1.0" encoding="UTF-8"?>
<ncx version="2005-1" xmlns="http://www.daisy.org/z3986/2005/ncx/">
    <head>
        <meta name="dtb:uid" content="{epub_id}"/>
        <meta name="dtb:depth" content="1"/>
        <meta name="dtb:totalPageCount" content="0"/>
        <meta name="dtb:maxPageNumber" content="0"/>
    </head>

    <docTitle>
        <text>{title}</text>
    </docTitle>

    <docAuthor>
        <text>{author}</text>
    </docAuthor>

    <navMap>{nav_points_str}
    </navMap>
</ncx>"""

    def _create_epub_css(self) -> str:
        """Create CSS specifically optimized for EPUB readers."""
        return """/* EPUB-optimized CSS for children's book */

body {
    font-family: "Georgia", "Times New Roman", serif;
    line-height: 1.6;
    color: #2c3e50;
    margin: 0;
    padding: 1em;
}

/* Typography */
h1, h2, h3 {
    color: #1565C0;
    margin-top: 1.5em;
    margin-bottom: 1em;
    page-break-after: avoid;
}

h1 {
    font-size: 2em;
    text-align: center;
}

h2 {
    font-size: 1.5em;
    border-bottom: 2px solid #27ae60;
    padding-bottom: 0.3em;
}

/* Paragraphs */
p {
    margin-bottom: 1em;
    text-align: justify;
    orphans: 2;
    widows: 2;
}

/* Special content boxes */
.quote-box, .learning-box, .important-box {
    border: 2px solid #2989d8;
    border-radius: 8px;
    padding: 1em;
    margin: 1.5em 0;
    background: #f8f9fa;
    page-break-inside: avoid;
}

/* Poem boxes with enhanced spacing - colors work in both light and dark modes */
.poem-box, .haiku-box, .limerick-box, .cinquain-box, .chant-box, .song-lyrics {
    border: 2px solid #4A7C59;
    border-radius: 8px;
    padding: 1.5em;
    margin: 2em 0;
    text-align: center;
    font-style: italic;
    background: #F5F5F5;
    color: #2C5530;
    page-break-inside: avoid;
}

.haiku-box {
    border-color: #f39c12;
    background: linear-gradient(135deg, #fff3cd 0%, #ffe69c 100%);
}

.limerick-box {
    border-color: #2196f3;
    background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
}

.cinquain-box {
    border-color: #9c27b0;
    background: linear-gradient(135deg, #f3e5f5 0%, #e1bee7 100%);
}

.chant-box {
    border-color: #996633;
    background: #FFF8F0;
    color: #663300;
    font-weight: bold;
}

.song-lyrics {
    border-color: #8B5A3C;
    background: #FFF5EE;
    color: #5C3317;
}

/* Images */
img {
    max-width: 100%;
    height: auto;
    display: block;
    margin: 1em auto;
    border-radius: 8px;
}

.caption {
    font-size: 0.9em;
    color: #7f8c8d;
    font-style: italic;
    text-align: center;
    margin-top: 0.5em;
}

/* Dialogue */
.dialogue {
    color: #d35400;
    font-style: italic;
}

/* Emphasis */
.emphasis {
    font-weight: bold;
    font-style: italic;
}

.highlight {
    background: #fff3cd;
    padding: 0.2em 0.4em;
    border-radius: 3px;
    font-weight: 600;
}

/* Page breaks */
.page-spread, .cover-page, .title-page, .table-of-contents, .preface,
.about-author, .acknowledgments, .index {
    page-break-before: always;
}

/* Table of Contents */
.toc-entry {
    display: flex;
    justify-content: space-between;
    padding: 0.5em 0;
    border-bottom: 1px dotted #ccc;
}

.chapter-name {
    font-weight: 600;
}

.page-ref {
    color: #7db9e8;
    font-style: italic;
}

/* Index */
.index-entry {
    display: flex;
    justify-content: space-between;
    padding: 0.3em 0;
    border-bottom: 1px dotted #ddd;
}

.term {
    font-weight: 600;
}

.page-refs {
    color: #7db9e8;
    font-style: italic;
}

/* Front Cover page with image background */
.front-cover-page {
    position: relative;
    width: 100%;
    height: 100vh;
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: center;
}

.cover-background {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    z-index: 1;
}

.cover-background-image {
    width: 100%;
    height: 100%;
    max-width: 100%;
    max-height: 100vh;
    object-fit: contain;
    object-position: center;
}

.cover-text-overlay {
    position: relative;
    z-index: 2;
    text-align: center;
    color: white;
    padding: 2em;
    background: rgba(0, 0, 0, 0.7);
    border-radius: 15px;
    backdrop-filter: blur(5px);
    border: 2px solid rgba(255, 255, 255, 0.3);
}

.front-cover-title {
    font-size: 3em;
    font-weight: bold;
    margin: 0.5em 0;
    text-shadow:
        3px 3px 6px rgba(0,0,0,0.9),
        -1px -1px 3px rgba(0,0,0,0.8),
        1px 1px 10px rgba(0,0,0,1);
    line-height: 1.2;
    letter-spacing: 0.02em;
}

.front-cover-subtitle {
    font-size: 2em;
    margin: 0.8em 0;
    font-style: italic;
    text-shadow:
        2px 2px 4px rgba(0,0,0,0.9),
        -1px -1px 2px rgba(0,0,0,0.8),
        1px 1px 8px rgba(0,0,0,1);
}

.front-cover-author {
    font-size: 1.5em;
    margin: 1.5em 0;
    text-shadow:
        2px 2px 4px rgba(0,0,0,0.9),
        -1px -1px 2px rgba(0,0,0,0.8),
        1px 1px 8px rgba(0,0,0,1);
}

.front-cover-publisher {
    font-size: 1.2em;
    margin: 1em 0;
    text-shadow:
        2px 2px 4px rgba(0,0,0,0.9),
        -1px -1px 2px rgba(0,0,0,0.8),
        1px 1px 8px rgba(0,0,0,1);
}

/* Back Cover page with image background */
.back-cover-page {
    position: relative;
    width: 100%;
    height: 100vh;
    overflow: hidden;
    display: flex;
    flex-direction: column;
}

.back-cover-text-overlay {
    position: relative;
    z-index: 2;
    height: 100%;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    padding: 2em;
    color: white;
}

.back-cover-content {
    flex-grow: 1;
    display: flex;
    flex-direction: column;
    justify-content: center;
    max-height: 70vh;
    overflow: hidden;
}

.back-cover-description {
    font-size: 1em;
    line-height: 1.5;
    text-align: center;
    background: rgba(0, 0, 0, 0.75);
    padding: 1.5em;
    border-radius: 10px;
    margin: 1em auto;
    color: white;
    font-weight: 400;
    border: 2px solid rgba(255, 255, 255, 0.2);
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.4);
    max-width: 90%;
    text-shadow:
        2px 2px 4px rgba(0,0,0,0.9),
        -1px -1px 2px rgba(0,0,0,0.8);
}

.back-cover-footer {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    margin-top: auto;
    background: rgba(0, 0, 0, 0.7);
    padding: 1em;
    border-radius: 8px;
}

.publisher-info {
    text-align: left;
}

.back-cover-publisher {
    font-size: 1em;
    font-weight: bold;
    margin: 0.2em 0;
    color: white;
    text-shadow:
        2px 2px 4px rgba(0,0,0,0.9),
        -1px -1px 2px rgba(0,0,0,0.8);
}

.back-cover-location {
    font-size: 0.9em;
    margin: 0.2em 0;
    color: white;
    text-shadow:
        2px 2px 4px rgba(0,0,0,0.9),
        -1px -1px 2px rgba(0,0,0,0.8);
}

.isbn-logo-section {
    text-align: right;
    display: flex;
    flex-direction: column;
    align-items: flex-end;
}

.isbn {
    font-size: 0.85em;
    margin: 0.5em 0;
    color: white;
    font-weight: bold;
    text-shadow:
        2px 2px 4px rgba(0,0,0,0.9),
        -1px -1px 2px rgba(0,0,0,0.8);
}

.back-cover-logo {
    max-width: 120px;
    height: auto;
    margin-top: 0.5em;
}

/* Explicit Title Page */
.explicit-title-page {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    text-align: center;
    padding: 3em;
}

.title-page-content {
    max-width: 600px;
}

.title-page-title {
    font-size: 3.5em;
    font-weight: bold;
    margin: 1em 0;
    color: #1565C0;
    line-height: 1.2;
}

.title-page-subtitle {
    font-size: 2.2em;
    margin: 1em 0;
    font-style: italic;
    color: #27ae60;
}

.title-page-author {
    font-size: 1.8em;
    margin: 2em 0;
    color: #2c3e50;
}

/* Powered by FableFlow section */
.powered-by-section {
    margin: 3em 0;
    padding: 2em;
    border-top: 2px solid #1565C0;
    border-bottom: 2px solid #1565C0;
    text-align: center;
}

.powered-by-text {
    font-size: 1.2em;
    color: #666;
    margin-bottom: 1em;
    font-style: italic;
}

.fableflow-logo {
    max-width: 250px;
    height: auto;
    margin: 0 auto;
    display: block;
}

.title-page-publisher {
    font-size: 1.3em;
    margin: 1.5em 0;
    color: #7f8c8d;
}

/* Publication Info Page */
.publication-info {
    padding: 4em 2em;
    text-align: center;
    line-height: 2;
    min-height: 80vh;
    display: flex;
    flex-direction: column;
    justify-content: center;
}

.pub-publisher {
    font-size: 1.3em;
    font-weight: bold;
    margin: 0.5em 0;
    color: #1565C0;
}

.pub-edition {
    font-size: 1.1em;
    color: #666;
    margin: 0.3em 0;
}

.pub-spacing {
    height: 2em;
}

.pub-credits {
    font-size: 1em;
    line-height: 1.8;
    color: #2c3e50;
}

.pub-copyright {
    font-size: 1em;
    font-weight: 600;
    color: #2c3e50;
}

.pub-isbn {
    font-size: 1.1em;
    margin: 2em 0;
    font-weight: bold;
    color: #1565C0;
}

.pub-disclaimer {
    font-size: 0.9em;
    font-style: italic;
    color: #666;
    max-width: 500px;
    margin: 2em auto;
    line-height: 1.6;
}

/* Responsive adjustments for different e-readers */
@media screen and (max-width: 600px) {
    body {
        padding: 0.5em;
    }

    .front-cover-title {
        font-size: 2em;
    }

    .front-cover-subtitle {
        font-size: 1.4em;
    }

    .title-page-title {
        font-size: 2.5em;
    }

    .back-cover-footer {
        flex-direction: column;
        align-items: center;
        text-align: center;
    }

    .isbn-logo-section {
        align-items: center;
        margin-top: 1em;
    }
}"""

    def _add_html_chapters(
        self, epub_zip: zipfile.ZipFile, soup: BeautifulSoup, book_metadata: dict
    ) -> None:
        """Add HTML chapters to the EPUB using BookStructureGenerator."""

        # Create structure generator for consistent front matter
        structure_gen = BookStructureGenerator(self.output_dir, book_metadata, format="epub")

        # 1. Cover page - simplified cover for EPUB readers/bookshelves
        # This is what EPUB readers display in library/bookshelf views
        cover_html = self._create_front_cover_page(book_metadata)
        epub_zip.writestr("OEBPS/cover.xhtml", cover_html)

        # 2. Front Cover page - convert HTML to XHTML
        front_cover_html = self._html_to_xhtml(
            book_metadata["title"], structure_gen.generate_front_cover_html()
        )
        epub_zip.writestr("OEBPS/front-cover.xhtml", front_cover_html)

        # 3. Title page with FableFlow logo
        title_html = self._html_to_xhtml(
            book_metadata["title"], structure_gen.generate_title_page_html()
        )
        epub_zip.writestr("OEBPS/title-page.xhtml", title_html)

        # 4. Publication Info page
        publication_info_html = self._html_to_xhtml(
            "Publication Information", structure_gen.generate_publication_info_html()
        )
        epub_zip.writestr("OEBPS/publication-info.xhtml", publication_info_html)

        # 5. Table of Contents page
        toc_element = soup.find("div", class_="table-of-contents")
        toc_html = self._create_xhtml_page("Table of Contents", toc_element)
        epub_zip.writestr("OEBPS/toc-page.xhtml", toc_html)

        # 6. Navigation file (EPUB 3 requirement)
        nav_html = self._create_nav_xhtml(book_metadata["title"])
        epub_zip.writestr("OEBPS/nav.xhtml", nav_html)

        # 7. Preface
        preface_element = soup.find("div", class_="preface")
        preface_html = self._create_xhtml_page("Preface", preface_element)
        epub_zip.writestr("OEBPS/preface.xhtml", preface_html)

        # 8. Main content (story chapters)
        story_content = self._extract_story_content(soup)
        content_html = self._create_xhtml_page("Story", story_content, content_type="story")
        epub_zip.writestr("OEBPS/content.xhtml", content_html)

        # 9. About the author
        about_element = soup.find("div", class_="about-author")
        about_html = self._create_xhtml_page("About the Author", about_element)
        epub_zip.writestr("OEBPS/about.xhtml", about_html)

        # 10. Index
        index_element = soup.find("div", class_="index")
        index_html = self._create_xhtml_page("Index", index_element)
        epub_zip.writestr("OEBPS/index.xhtml", index_html)

        # 11. Back Cover page
        back_cover_html = self._html_to_xhtml(
            book_metadata["title"], structure_gen.generate_back_cover_html()
        )
        epub_zip.writestr("OEBPS/back-cover.xhtml", back_cover_html)

    def _html_to_xhtml(self, title: str, html_content: str) -> str:
        """Convert HTML fragment to proper XHTML page for EPUB.

        Uses EPUB 3 compatible XHTML structure.

        Args:
            title: Page title
            html_content: HTML content fragment

        Returns:
            Complete XHTML page
        """
        # Fix image paths for EPUB
        html_content = BookContentProcessor.fix_image_paths_for_epub(html_content)

        return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
    <title>{title}</title>
    <link rel="stylesheet" type="text/css" href="styles/main.css"/>
</head>
<body>
    {html_content}
</body>
</html>"""

    # OLD METHODS - Now handled by BookStructureGenerator
    # Kept for backward compatibility but deprecated
    def _create_front_cover_page(self, book_metadata: dict) -> str:
        """Create a front cover page XHTML with image background and text overlays."""

        title = book_metadata.get("title", "FableFlow Book")
        subtitle = book_metadata.get("subtitle", "")
        # ALWAYS use config.book.draft_story_author for author attribution
        author = config.book.draft_story_author
        publisher = book_metadata.get("publisher", config.book.publisher)

        # Generate subtitle HTML only if subtitle exists and is not empty/None
        subtitle_html = ""
        if subtitle and subtitle.strip():
            subtitle_html = f'<h2 class="front-cover-subtitle">{subtitle}</h2>'
            logger.info(f"EPUBGenerator: Adding subtitle to cover: '{subtitle}'")
        else:
            logger.debug(f"EPUBGenerator: No subtitle for cover (value: '{subtitle}')")

        return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
    <title>Cover - {title}</title>
    <link rel="stylesheet" type="text/css" href="styles/main.css"/>
</head>
<body>
    <div class="front-cover-page">
        <div class="cover-background">
            <img src="images/front_cover.png" alt="Book Cover" class="cover-background-image"/>
        </div>
        <div class="cover-text-overlay">
            <h1 class="front-cover-title">{title}</h1>
            {subtitle_html}
            <p class="front-cover-author">By {author}</p>
            <p class="front-cover-publisher">{publisher}</p>
        </div>
    </div>
</body>
</html>"""

    def _create_back_cover_page(self, book_metadata: dict) -> str:
        """Create a back cover page XHTML with image background and text overlays."""
        from fable_flow.config import config

        title = book_metadata.get("title", "FableFlow Book")
        isbn = config.book.isbn_epub
        publisher = book_metadata.get("publisher", config.book.publisher)
        publisher_location = config.book.publisher_location

        return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
    <title>Back Cover - {title}</title>
    <link rel="stylesheet" type="text/css" href="styles/main.css"/>
</head>
<body>
    <div class="back-cover-page">
        <div class="cover-background">
            <img src="images/back_cover.png" alt="Back Cover" class="cover-background-image"/>
        </div>
        <div class="back-cover-text-overlay">
            <div class="back-cover-content">
                <div class="back-cover-description">
                    <p>An engaging educational children's book that combines storytelling with learning.</p>
                </div>
            </div>
            <div class="back-cover-footer">
                <div class="publisher-info">
                    <p class="back-cover-publisher">{publisher}</p>
                    <p class="back-cover-location">{publisher_location}</p>
                </div>
                <div class="isbn-logo-section">
                    <p class="isbn">ISBN {isbn}</p>
                    <img src="{_LOGO_PATH}" alt="FableFlow Logo" class="back-cover-logo"/>
                </div>
            </div>
        </div>
    </div>
</body>
</html>"""

    def _create_xhtml_page(
        self, title: str, content_element, content_type: str = "standard"
    ) -> str:
        """Create an XHTML page from BeautifulSoup element.

        Uses EPUB 3 compatible XHTML structure.
        """
        if content_element is None:
            content_html = f"<p><em>{title} content not available.</em></p>"
        else:
            content_html = str(content_element)
            # Convert div to section for better semantic structure
            content_html = content_html.replace("<div class=", "<section class=")
            content_html = content_html.replace("</div>", "</section>")

            # Fix image paths for EPUB structure
            content_html = self._fix_image_paths(content_html)

        return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
    <title>{title}</title>
    <link rel="stylesheet" type="text/css" href="styles/main.css"/>
</head>
<body>
    {content_html}
</body>
</html>"""

    def _create_nav_xhtml(self, title: str) -> str:
        """Create EPUB 3 navigation document.

        Required for EPUB 3 specification. Uses epub:type="toc" for semantic navigation.
        """
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
    <title>Navigation - {title}</title>
    <link rel="stylesheet" type="text/css" href="styles/main.css"/>
</head>
<body>
    <nav epub:type="toc" id="toc">
        <h1>Table of Contents</h1>
        <ol>
            <li><a href="front-cover.xhtml">Cover</a></li>
            <li><a href="title-page.xhtml">Title Page</a></li>
            <li><a href="publication-info.xhtml">Publication Info</a></li>
            <li><a href="toc-page.xhtml">Contents</a></li>
            <li><a href="preface.xhtml">Preface</a></li>
            <li><a href="content.xhtml">Story</a></li>
            <li><a href="about.xhtml">About the Author</a></li>
            <li><a href="index.xhtml">Index</a></li>
        </ol>
    </nav>
</body>
</html>"""

    def _extract_story_content(self, soup: BeautifulSoup):
        """Extract the main story content from the parsed HTML."""
        # Find all page spreads and pages that contain the story
        story_elements = []

        # Classes to skip (front matter and back matter)
        skip_classes = [
            "front-cover-page",  # Front cover from BookStructureGenerator
            "explicit-title-page",  # Title page from BookStructureGenerator
            "publication-info",  # Publication info from BookStructureGenerator
            "back-cover-page",  # Back cover from BookStructureGenerator
            "cover-page",  # Legacy cover page
            "title-page",  # Legacy title page
            "table-of-contents",  # TOC
            "preface",  # Preface
            "about-author",  # About author
            "acknowledgments",  # Acknowledgments
            "index",  # Index
        ]

        # Look for page spreads and individual pages
        pages = soup.find_all("div", class_=["page-spread", "page"])
        for page in pages:
            # Check if this page contains any skip classes
            page_html = str(page)
            should_skip = False

            for skip_class in skip_classes:
                if f'class="{skip_class}"' in page_html or f"class='{skip_class}'" in page_html:
                    should_skip = True
                    logger.debug(f"EPUBGenerator: Skipping page with class '{skip_class}'")
                    break

            if not should_skip:
                story_elements.append(page)

        # If no pages found, look for content directly
        if not story_elements:
            # Look for chapter content
            chapters = soup.find_all("h2", class_="chapter-title")
            for chapter in chapters:
                # Get the parent container
                parent = chapter.find_parent("div")
                if parent:
                    story_elements.append(parent)

        # Combine all story elements
        if story_elements:
            combined_content = soup.new_tag("div", **{"class": "story-content"})
            for element in story_elements:
                combined_content.append(element.extract())
            return combined_content

        # Fallback: return a placeholder
        placeholder = soup.new_tag("div", **{"class": "story-content"})
        placeholder.string = "Story content not found."
        return placeholder

    def _create_epub_cover_with_text(self, book_metadata: dict) -> Path:
        """Create EPUB cover by overlaying title, subtitle, author, and publisher on front cover image."""
        front_cover_path = self.output_dir / "front_cover.png"
        epub_cover_path = self.output_dir / "epub_cover.png"

        if epub_cover_path.exists():
            return epub_cover_path

        cover_img = Image.open(front_cover_path)
        width, height = cover_img.size
        draw = ImageDraw.Draw(cover_img)

        title = book_metadata.get("title", "Untitled")
        subtitle = book_metadata.get("subtitle", "")
        author = config.book.draft_story_author
        publisher = book_metadata.get("publisher", config.book.publisher)

        # Reasonable font sizes that fit on cover
        title_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", int(height * 0.08)
        )
        subtitle_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/liberation/LiberationSans-Italic.ttf", int(height * 0.05)
        )
        info_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", int(height * 0.04)
        )

        # Padding and spacing
        side_padding = int(width * 0.08)
        max_width = width - (2 * side_padding)
        section_spacing = int(height * 0.06)

        def wrap_text(text, font):
            """Wrap text to fit within max_width."""
            words = text.split()
            lines = []
            current_line = []

            for word in words:
                test_line = " ".join(current_line + [word])
                bbox = draw.textbbox((0, 0), test_line, font=font)
                if bbox[2] - bbox[0] <= max_width:
                    current_line.append(word)
                else:
                    if current_line:
                        lines.append(" ".join(current_line))
                    current_line = [word]

            if current_line:
                lines.append(" ".join(current_line))

            return lines

        def draw_text_block(lines, font, y_pos, color):
            """Draw centered text block with outline, return total height used."""
            line_spacing = int(height * 0.01)
            total_height = 0

            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                x_pos = (width - text_width) // 2

                # Black outline for readability
                for dx in [-2, -1, 0, 1, 2]:
                    for dy in [-2, -1, 0, 1, 2]:
                        if dx != 0 or dy != 0:
                            draw.text((x_pos + dx, y_pos + dy), line, font=font, fill=(0, 0, 0))

                # Main text
                draw.text((x_pos, y_pos), line, font=font, fill=color)
                y_pos += text_height + line_spacing
                total_height += text_height + line_spacing

            return total_height

        # Layout from top
        y = int(height * 0.25)

        # Title
        title_lines = wrap_text(title, title_font)
        y += draw_text_block(title_lines, title_font, y, (255, 255, 255))
        y += section_spacing

        # Subtitle
        if subtitle and subtitle.strip():
            subtitle_lines = wrap_text(subtitle, subtitle_font)
            y += draw_text_block(subtitle_lines, subtitle_font, y, (255, 220, 80))
            y += section_spacing

        # Author and publisher at bottom
        bottom_y = int(height * 0.85)

        author_lines = wrap_text(f"By {author}", info_font)
        publisher_lines = wrap_text(publisher, info_font)

        # Calculate total height needed for bottom section
        author_bbox = draw.textbbox((0, 0), "By Author", font=info_font)
        line_height = author_bbox[3] - author_bbox[1]
        bottom_content_height = (len(author_lines) + len(publisher_lines)) * line_height

        # Position author and publisher
        author_y = bottom_y - bottom_content_height
        author_y += draw_text_block(author_lines, info_font, author_y, (255, 255, 255))
        author_y += int(height * 0.02)
        draw_text_block(publisher_lines, info_font, author_y, (255, 255, 255))

        cover_img.save(epub_cover_path, "PNG")
        logger.info(f"EPUBGenerator: Created EPUB cover: {epub_cover_path}")

        return epub_cover_path

    def _collect_images(self) -> list:
        """Collect all images that need to be included in the EPUB."""
        # Use shared utility for consistent image collection
        image_files = BookContentProcessor.collect_images(
            self.output_dir, include_covers=True, include_logos=True
        )
        logger.info(f"EPUBGenerator: Collected {len(image_files)} images")
        return image_files

    def _generate_image_manifest_entries(self, image_files: list) -> str:
        """Generate manifest entries for all images.

        For EPUB 3, the cover image uses properties="cover-image" for better
        metadata support. Also maintains backwards-compatible meta reference.
        """
        if not image_files:
            return ""

        entries = []
        for i, image_file in enumerate(image_files):
            # Determine media type based on extension
            ext = image_file.suffix.lower()
            if ext == ".png":
                media_type = "image/png"
            elif ext in [".jpg", ".jpeg"]:
                media_type = "image/jpeg"
            elif ext == ".gif":
                media_type = "image/gif"
            elif ext == ".svg":
                media_type = "image/svg+xml"
            else:
                media_type = "image/png"  # fallback

            # Special handling for EPUB cover with text - give it the cover-image id
            # Uses both properties="cover-image" (EPUB 3) and meta reference (backwards compat)
            if image_file.name == "epub_cover.png":
                entries.append(
                    f'\n        <item id="cover-image" href="images/{image_file.name}" media-type="{media_type}" properties="cover-image"/>'
                )
            else:
                entries.append(
                    f'\n        <item id="img-{i}" href="images/{image_file.name}" media-type="{media_type}"/>'
                )

        return "".join(entries)

    def _fix_image_paths(self, content_html: str) -> str:
        """Fix image paths to point to the images directory in EPUB structure.

        Also handles malformed img tags for EPUB XML validation.
        """
        import re

        # STEP 1: Fix malformed img tags with ="" attributes (from unescaped quotes in alt text)
        def fix_malformed_img(match):
            """Fix img tags with broken alt attributes that create empty ="" attributes."""
            img_tag = match.group(0)

            # Extract essential attributes
            src_match = re.search(r'src=["\']([^"\']+)["\']', img_tag)
            alt_match = re.search(r'alt="([^"]*)"', img_tag)
            class_match = re.search(r'class=["\']([^"\']+)["\']', img_tag)

            if not src_match:
                return img_tag

            src = src_match.group(1)
            alt_text = alt_match.group(1) if alt_match else ""
            class_attr = f' class="{class_match.group(1)}"' if class_match else ""

            # Collect word="" fragments between alt and src
            if alt_match and "src=" in img_tag:
                alt_end = alt_match.end()
                src_start = img_tag.find("src=", alt_end)
                between = img_tag[alt_end:src_start]

                # Find all word="" patterns
                fragments = re.findall(r'(\S+)=""', between)
                if fragments:
                    alt_text = alt_text + " " + " ".join(fragments)
                    alt_text = alt_text.replace('"', "'").strip()
                    logger.info(
                        f"EPUBGenerator: Fixed malformed img with {len(fragments)} fragments"
                    )

            return f'<img src="{src}"{class_attr} alt="{alt_text}"/>'

        # Look for malformed img tags (multiple ="" patterns)
        malformed_pattern = r'<img[^>]*=""[^>]*=""[^>]*>'
        content_html = re.sub(malformed_pattern, fix_malformed_img, content_html, flags=re.DOTALL)

        # STEP 2: Fix image paths to use images/ directory
        img_pattern = r'<img([^>]*?)src=["\']([^"\']*?)["\']([^>]*?)>'

        def replace_img_src(match):
            before_src = match.group(1)
            src_path = match.group(2)
            after_src = match.group(3)

            # Extract just the filename from the path
            filename = Path(src_path).name

            # Update path to EPUB images directory
            new_src = f"images/{filename}"

            return f'<img{before_src}src="{new_src}"{after_src}>'

        # Replace all image sources
        fixed_content = re.sub(img_pattern, replace_img_src, content_html)

        return fixed_content

    def _add_images_to_epub(self, epub_zip: zipfile.ZipFile, image_files: list) -> None:
        """Add images to the EPUB with proper paths."""
        images_added = 0

        for image_file in image_files:
            try:
                epub_path = f"OEBPS/images/{image_file.name}"
                with open(image_file, "rb") as img_file:
                    epub_zip.writestr(epub_path, img_file.read())
                images_added += 1
                logger.debug(f"EPUBGenerator: Added image {image_file.name}")
            except Exception as e:
                logger.warning(f"EPUBGenerator: Failed to add image {image_file.name}: {e}")

        logger.info(f"EPUBGenerator: Added {images_added} images to EPUB")

    def _create_fallback_epub(
        self, epub_path: Path, title: str, author: str, html_content: str
    ) -> None:
        """Create a simple fallback EPUB if main generation fails."""
        try:
            with zipfile.ZipFile(epub_path, "w", zipfile.ZIP_DEFLATED) as epub_zip:
                # Basic EPUB structure
                epub_zip.writestr(
                    "mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED
                )

                # Container
                container_xml = self._create_container_xml()
                epub_zip.writestr("META-INF/container.xml", container_xml)

                # Simple content.opf
                simple_opf = f"""<?xml version="1.0" encoding="UTF-8"?>
<package version="3.0" xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookId">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
        <dc:identifier id="BookId">fallback-{uuid.uuid4()}</dc:identifier>
        <dc:title>{title}</dc:title>
        <dc:creator>{author}</dc:creator>
        <dc:language>en</dc:language>
        <meta property="dcterms:modified">{datetime.now().isoformat()}</meta>
    </metadata>
    <manifest>
        <item id="content" href="content.xhtml" media-type="application/xhtml+xml"/>
        <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    </manifest>
    <spine toc="ncx">
        <itemref idref="content"/>
    </spine>
</package>"""
                epub_zip.writestr("OEBPS/content.opf", simple_opf)

                # Simple content
                soup = BeautifulSoup(html_content, "html.parser")
                text_content = soup.get_text()

                simple_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>{title}</title>
</head>
<body>
    <h1>{title}</h1>
    <p>By {author}</p>
    <div style="white-space: pre-line;">{text_content[:5000]}...</div>
</body>
</html>"""
                epub_zip.writestr("OEBPS/content.xhtml", simple_content)

                # Simple NCX
                simple_ncx = f"""<?xml version="1.0" encoding="UTF-8"?>
<ncx version="2005-1" xmlns="http://www.daisy.org/z3986/2005/ncx/">
    <head>
        <meta name="dtb:uid" content="fallback"/>
    </head>
    <docTitle><text>{title}</text></docTitle>
    <navMap>
        <navPoint id="content" playOrder="1">
            <navLabel><text>Content</text></navLabel>
            <content src="content.xhtml"/>
        </navPoint>
    </navMap>
</ncx>"""
                epub_zip.writestr("OEBPS/toc.ncx", simple_ncx)

            logger.info(f"EPUBGenerator: Fallback EPUB created: {epub_path}")

        except Exception as e:
            logger.error(f"EPUBGenerator: Even fallback EPUB creation failed: {e}")

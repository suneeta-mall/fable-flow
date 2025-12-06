import re
import shutil
from pathlib import Path
from typing import Any, Optional

from bs4 import BeautifulSoup, NavigableString
from loguru import logger
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    KeepTogether,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)
from reportlab.platypus import Image as RLImage
from reportlab.platypus.tableofcontents import SimpleIndex

from fable_flow.book_structure import BookStructureGenerator
from fable_flow.book_utils import BookContentProcessor
from fable_flow.common import Manuscript
from fable_flow.config import config

_LOGO_PATH = Path(__file__).parent.parent.parent / "docs" / "assets" / "logo_horizontal.png"


class BookmarkFlowable(Spacer):
    """A flowable that creates PDF bookmarks and tracks page numbers.

    This creates both:
    1. Internal PDF bookmarks (for the navigation panel/outline)
    2. Page number tracking (for TOC page references)
    """

    def __init__(self, key: str, title: str, page_tracker: dict[str, int]):
        """Initialize bookmark.

        Args:
            key: Unique bookmark identifier
            title: Display title for the bookmark
            page_tracker: Dictionary to store bookmark -> page number mapping
        """
        super().__init__(0, 0)  # Zero height spacer
        self.key = key
        self.title = title
        self.page_tracker = page_tracker

    def draw(self):
        """Draw the bookmark (called when rendering the page)."""
        canvas = self.canv
        # Create PDF bookmark/outline entry
        canvas.bookmarkPage(self.key)
        canvas.addOutlineEntry(self.title, self.key, level=0)
        # Track the page number
        self.page_tracker[self.key] = canvas.getPageNumber()
        logger.debug(
            f"PDFGenerator: Created PDF bookmark '{self.key}' on page {canvas.getPageNumber()}"
        )


class PDFGenerator:
    FORMAL_BOOK_CLASSES = [
        "front-cover-page",
        "back-cover-page",
        "explicit-title-page",
        "publication-info",
        "title-page",
        "table-of-contents",
        "preface",
        "about-author",
        "acknowledgments",
        "index",
    ]

    PAGE_CLASSES = ["page", "page-spread"]

    POEM_CLASSES = [
        "poem-box",
        "poem-verse",
        "chant-box",
        "song-lyrics",
        "haiku-box",
        "limerick-box",
        "cinquain-box",
    ]

    def _is_descendant_of(self, child, parent):
        """Check if child element is a descendant of parent element."""
        if not child or not parent:
            return False
        current = child.parent
        while current:
            if current == parent:
                return True
            current = current.parent
        return False

    IMAGE_CLASSES = [
        "image-inline",
        "image-full-page",
        "image-spread",
        "image-inline-left",
        "image-inline-right",
        "image-chapter-opener",
    ]

    BACK_MATTER_CLASSES = ["about-author", "acknowledgments", "index"]

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self._image_reference_map: dict[str, Any] = {}
        self._current_page_number = config.style.pdf.start_page_number
        self._chapter_bookmarks: dict[str, str] = {}  # Maps chapter title to bookmark name
        self._section_bookmarks: dict[str, str] = {}  # Maps section title to bookmark name
        self._bookmark_pages: dict[str, int] = {}  # Maps bookmark name to page number
        self._chapter_counter = 0  # Counter for generating unique bookmark IDs
        self._section_counter = 0  # Counter for generating unique section bookmark IDs
        # Calculate available frame dimensions once (accounting for margins and padding)
        pdf_config = config.style.pdf
        frame_width = pdf_config.page_size[0] - pdf_config.margin_left - pdf_config.margin_right
        frame_height = pdf_config.page_size[1] - pdf_config.margin_top - pdf_config.margin_bottom
        # Account for frame padding and footer space
        self._available_width = frame_width - (0.4 * inch)  # leftPadding + rightPadding
        self._available_height = (
            frame_height - 0.5 * inch - (0.4 * inch)
        )  # footer + top/bottom padding

        # Cover-specific dimensions: maximize image size with minimal padding
        # Covers use special template with minimal margins (0.05 inch)
        cover_margin = 0.05 * inch
        self._cover_max_width = (
            pdf_config.page_size[0] - (2 * cover_margin) - (0.1 * inch)
        )  # Safety
        self._cover_max_height = (
            pdf_config.page_size[1] - (2 * cover_margin) - (0.1 * inch)
        )  # Safety

    def generate_pdf(
        self,
        html_content: str,
        message: Manuscript,
        output_path: Path,
        book_metadata: dict | None = None,
    ) -> None:
        """Generate a PDF from HTML content with images and formatting - SIMPLIFIED."""
        logger.info(f"PDFGenerator: Generating PDF from HTML with {len(html_content)} characters")

        # Store book metadata for regenerating cover/title pages
        self._book_metadata = book_metadata or {}

        # Reset chapter and section tracking for new PDF generation
        self._chapter_bookmarks = {}
        self._section_bookmarks = {}
        self._bookmark_pages = {}
        self._chapter_counter = 0
        self._section_counter = 0

        # Clean HTML content using shared utility
        html_content = BookContentProcessor.clean_html_content(html_content)
        logger.info(f"PDFGenerator: Cleaned HTML content, now {len(html_content)} characters")

        # Pre-extract image references using shared utility
        self._image_reference_map = BookContentProcessor.extract_image_references(html_content)
        logger.info(
            f"PDFGenerator: Pre-extracted {len(self._image_reference_map)} image references"
        )

        # Parse HTML structure
        soup = BeautifulSoup(html_content, "html.parser")
        book_div = soup.find("div", class_="book")

        # Pre-scan all chapters and sections to build bookmark mapping BEFORE processing TOC
        self._prescan_chapters_and_sections(soup)
        logger.info(
            f"PDFGenerator: Pre-scanned {len(self._chapter_bookmarks)} chapters and {len(self._section_bookmarks)} sections for TOC navigation"
        )

        # Create document with config settings
        doc = self._create_document(output_path)

        # Process all elements - front matter (outside book div) + book content
        all_elements = []
        back_cover_element = None  # Keep back cover separate to add at end

        # First, collect front matter elements (cover, title page, etc.) that are siblings of book div
        # EXCLUDE back cover from front matter - it goes at the end
        if book_div:
            # Look for page-spread elements that come before the book div (front matter)
            for elem in soup.find_all("div", class_="page-spread"):
                if elem != book_div and not self._is_descendant_of(elem, book_div):
                    # Check if this page-spread contains formal book classes
                    # Look for formal classes nested anywhere inside (could be page > formal-class)
                    formal_children = elem.find_all(
                        "div",
                        class_=lambda cls: cls
                        and any(
                            c in self.FORMAL_BOOK_CLASSES
                            for c in (cls if isinstance(cls, list) else [cls])
                        ),
                    )
                    if formal_children:
                        # Check if this is the back cover - if so, save it for later
                        formal_classes = [
                            c for child in formal_children for c in child.get("class", [])
                        ]
                        if "back-cover-page" in formal_classes:
                            back_cover_element = elem
                            logger.info("PDFGenerator: Found back cover - will add at end")
                            continue  # Skip adding to all_elements

                        logger.info(
                            f"PDFGenerator: Found front matter page-spread with formal classes: {formal_classes}"
                        )
                        all_elements.append(elem)
                    elif any(cls in elem.get("class", []) for cls in self.FORMAL_BOOK_CLASSES):
                        # Check if it's back cover
                        if "back-cover-page" not in elem.get("class", []):
                            all_elements.append(elem)

            # Then get direct children of book div that match our target classes
            for elem in book_div.find_all("div", recursive=False):
                elem_classes = elem.get("class", [])
                if any(
                    cls in elem_classes for cls in (self.PAGE_CLASSES + self.FORMAL_BOOK_CLASSES)
                ):
                    all_elements.append(elem)

            # Also get any top-level formal elements that might not be direct children
            for elem in book_div.find_all("div"):
                elem_classes = elem.get("class", [])
                if any(cls in elem_classes for cls in self.FORMAL_BOOK_CLASSES):
                    # Only add if it's not already included and not nested inside a page-spread
                    if elem not in all_elements and not elem.find_parent(
                        "div", class_="page-spread"
                    ):
                        all_elements.append(elem)
        else:
            # No book div found, process all page-spread elements
            logger.warning("PDFGenerator: No book div found, processing all page-spread elements")
            for elem in soup.find_all("div", class_="page-spread"):
                all_elements.append(elem)

        # Count different types of elements for logging
        page_elements = [
            e for e in all_elements if any(cls in e.get("class", []) for cls in self.PAGE_CLASSES)
        ]
        formal_elements = [
            e
            for e in all_elements
            if any(cls in e.get("class", []) for cls in self.FORMAL_BOOK_CLASSES)
        ]

        logger.info(
            f"PDFGenerator: Processing {len(page_elements)} page elements and {len(formal_elements)} formal book elements"
        )
        logger.info(f"PDFGenerator: Total elements to process: {len(all_elements)}")

        story_elements = self._process_pages(all_elements)

        # Add back cover at the END after all content
        if back_cover_element:
            logger.info("PDFGenerator: Adding back cover at end of document")
            # Ensure back cover starts on a new page
            story_elements.append(PageBreak())
            back_cover_pages = self._process_pages([back_cover_element])
            story_elements.extend(back_cover_pages)

        # Build PDF (two-pass approach for accurate page numbers)
        try:
            # First pass: Build to track page numbers
            logger.info("PDFGenerator: First pass - building PDF to track page numbers")
            doc.build(story_elements)

            # Check if we have page numbers now
            if self._bookmark_pages:
                logger.info(
                    f"PDFGenerator: Page numbers tracked: {len(self._bookmark_pages)} bookmarks"
                )

                # Second pass: Rebuild with accurate page numbers in TOC
                # Only do second pass if TOC exists and we have page numbers
                has_toc = any("table-of-contents" in str(elem) for elem in all_elements[:5])
                if has_toc:
                    logger.info("PDFGenerator: Second pass - rebuilding with accurate page numbers")

                    # Rebuild the document with the same elements
                    # (TOC will now use actual page numbers from _bookmark_pages)
                    doc = self._create_document(output_path)
                    story_elements = self._process_pages(all_elements)

                    # Add back cover at the END after all content (second pass)
                    if back_cover_element:
                        story_elements.append(PageBreak())
                        back_cover_pages = self._process_pages([back_cover_element])
                        story_elements.extend(back_cover_pages)

                    doc.build(story_elements)
                    logger.info("PDFGenerator: Second pass complete with accurate page numbers")

            logger.info(f"PDFGenerator: PDF generated successfully: {output_path}")
        except Exception as e:
            logger.error(f"PDFGenerator: PDF generation failed: {e}")
            # Delete partial file if it exists
            if output_path.exists():
                output_path.unlink()
                logger.info(f"PDFGenerator: Deleted partial PDF file: {output_path}")
            # Re-raise exception to stop processing
            raise

    def _prescan_chapters_and_sections(self, soup: BeautifulSoup) -> None:
        """Pre-scan HTML to find all chapters and sections, create bookmark mappings.

        This must be done before processing the TOC so that TOC links can reference
        content that comes later in the document.

        Scans for:
        - Chapter titles (h2.chapter-title)
        - Preface (div.preface)
        - About Author (div.about-author)
        - Acknowledgments (div.acknowledgments)
        - Index (div.index)
        """
        # Scan chapters
        chapter_titles = soup.find_all("h2", class_="chapter-title")
        for chapter_h2 in chapter_titles:
            chapter_text = chapter_h2.get_text().strip()
            if chapter_text and chapter_text not in self._chapter_bookmarks:
                bookmark_name = f"chapter_{self._chapter_counter}"
                self._chapter_bookmarks[chapter_text] = bookmark_name
                self._chapter_counter += 1
                logger.debug(
                    f"PDFGenerator: Pre-scanned chapter '{chapter_text}' -> bookmark '{bookmark_name}'"
                )

        # Scan formal book sections
        section_mappings = [
            ("preface", "Preface"),
            ("about-author", "About the Author"),
            ("acknowledgments", "Acknowledgments"),
            ("index", "Index"),
        ]

        for class_name, default_title in section_mappings:
            section_divs = soup.find_all("div", class_=class_name)
            for section_div in section_divs:
                # Try to find the section title (h1 or h2)
                title_elem = section_div.find(["h1", "h2"])
                section_title = title_elem.get_text().strip() if title_elem else default_title

                if section_title and section_title not in self._section_bookmarks:
                    bookmark_name = f"section_{self._section_counter}"
                    self._section_bookmarks[section_title] = bookmark_name
                    self._section_counter += 1
                    logger.debug(
                        f"PDFGenerator: Pre-scanned section '{section_title}' -> bookmark '{bookmark_name}'"
                    )

    def _create_document(self, output_path: Path) -> BaseDocTemplate:
        """Create the PDF document with proper configuration."""
        pdf_config = config.style.pdf
        doc = BaseDocTemplate(
            str(output_path),
            pagesize=pdf_config.page_size,
            topMargin=pdf_config.margin_top,
            bottomMargin=pdf_config.margin_bottom,
            leftMargin=pdf_config.margin_left,
            rightMargin=pdf_config.margin_right,
        )

        # Define COVER frame with minimal margins (for full-page covers)
        cover_margin = 0.05 * inch  # Minimal margin for safety
        cover_frame = Frame(
            cover_margin,
            cover_margin,
            pdf_config.page_size[0] - (2 * cover_margin),
            pdf_config.page_size[1] - (2 * cover_margin),
            leftPadding=0,
            rightPadding=0,
            topPadding=0,
            bottomPadding=0,
        )

        # Define content frame
        frame_width = pdf_config.page_size[0] - pdf_config.margin_left - pdf_config.margin_right
        frame_height = pdf_config.page_size[1] - pdf_config.margin_top - pdf_config.margin_bottom

        content_frame = Frame(
            pdf_config.margin_left,
            pdf_config.margin_bottom + 0.5 * inch,  # Leave space for page numbers
            frame_width,
            frame_height - 0.5 * inch,  # Reduce content height to make room for footer
            leftPadding=0.2 * inch,
            rightPadding=0.2 * inch,
            topPadding=0.2 * inch,
            bottomPadding=0.2 * inch,
        )

        # Create page template with footer for page numbers
        def add_page_number(canvas, doc):
            canvas.saveState()
            canvas.setFont("Helvetica", 10)
            page_num = f"— {canvas.getPageNumber()} —"
            canvas.drawCentredString(
                pdf_config.page_size[0] / 2, pdf_config.margin_bottom / 2, page_num
            )
            canvas.restoreState()

        # Create two page templates: one for covers (no page numbers), one for content
        cover_template = PageTemplate(id="cover", frames=[cover_frame])
        page_template = PageTemplate(id="normal", frames=[content_frame], onPage=add_page_number)
        doc.addPageTemplates([cover_template, page_template])
        return doc

    def _process_pages(self, pages) -> list:
        """Process all pages and return story elements."""
        story_elements = []
        styles = self._create_styles()
        processed_elements = set()

        for i, page_element in enumerate(pages):
            is_last_page = i == len(pages) - 1
            page_id = id(page_element)

            if page_id in processed_elements:
                continue

            # Check if this page contains a chapter title
            has_chapter = bool(page_element.find("h2", class_="chapter-title"))

            # Only add page break before new chapter if it's not the first element
            # and the previous element wasn't also a chapter (avoid double breaks)
            if has_chapter and i > 0:
                # Check if previous element was also a page-spread with chapter
                prev_was_chapter = False
                if i > 0:
                    prev_element = pages[i - 1]
                    prev_was_chapter = bool(prev_element.find("h2", class_="chapter-title"))

                # Only add page break if previous wasn't a chapter (avoid consecutive breaks)
                if not prev_was_chapter:
                    story_elements.append(PageBreak())

            if "page-spread" in page_element.get("class", []):
                # Handle page spreads - process all pages in the spread together
                individual_pages = page_element.find_all("div", class_="page")
                for j, individual_page in enumerate(individual_pages):
                    # Always add page break before each .page div (except the first)
                    # This ensures every .page div starts on a new page
                    if j > 0:
                        story_elements.append(PageBreak())

                    page_elements = self._process_single_page(individual_page, styles)
                    story_elements.extend(page_elements)
                    processed_elements.add(id(individual_page))

                # Add page break after page-spread based on what comes next
                if not is_last_page and i + 1 < len(pages):
                    next_element = pages[i + 1]
                    next_has_chapter = bool(next_element.find("h2", class_="chapter-title"))
                    next_has_back_matter = any(
                        cls in next_element.get("class", []) or next_element.find("div", class_=cls)
                        for cls in self.BACK_MATTER_CLASSES
                    )

                    # Add page break before new chapters or back matter
                    if next_has_chapter or next_has_back_matter:
                        story_elements.append(PageBreak())
            else:
                # Handle single page
                page_elements = self._process_single_page(page_element, styles)
                story_elements.extend(page_elements)
                processed_elements.add(page_id)

                # Add page break after EVERY page div to ensure clean page starts
                # (except after the last page)
                if not is_last_page:
                    story_elements.append(PageBreak())

        return story_elements

    def _process_single_page(self, page_element, styles) -> list:
        """Process content of a single page element or formal book element."""
        elements: list[Any] = []
        processed_elements: set[Any] = set()
        page_classes = page_element.get("class", [])

        # Handle formal book elements directly
        if any(cls in page_classes for cls in self.FORMAL_BOOK_CLASSES):
            return self._process_div_element(page_element, styles, processed_elements)

        # CRITICAL FIX: Check if this page contains a formal book element as a direct child
        # This handles the structure: <div class="page"><div class="front-cover-page">...</div></div>
        for child in page_element.children:
            if hasattr(child, "get") and hasattr(child, "name") and child.name == "div":
                child_classes = child.get("class", [])
                if any(cls in child_classes for cls in self.FORMAL_BOOK_CLASSES):
                    logger.info(
                        f"PDFGenerator: Found formal book element inside page: {child_classes}"
                    )
                    return self._process_div_element(child, styles, processed_elements)

        # Check if this is a chapter page
        has_chapter = bool(page_element.find("h2", class_="chapter-title"))

        # Add extra space before chapter title
        if has_chapter:
            elements.append(Spacer(1, 0.3 * 72))

        for child in page_element.children:
            if isinstance(child, NavigableString):
                continue

            child_id = id(child)
            if child_id in processed_elements:
                continue

            element_type = child.name
            classes = child.get("class", [])

            if element_type == "h1" and "book-title" in classes:
                text = child.get_text().strip()
                elements.append(self._create_paragraph(text, styles["book-title"]))
                processed_elements.add(child_id)

            elif element_type == "h2" and "chapter-title" in classes:
                parent_div = child.find_parent("div", class_="chapter-opener")
                if not parent_div:
                    elements.append(Spacer(1, 0.3 * 72))
                    text = child.get_text().strip()
                    # Use pre-scanned bookmark for this chapter
                    bookmark_name = self._chapter_bookmarks.get(text)
                    if bookmark_name:
                        # Add PDF bookmark for outline navigation and page tracking
                        elements.append(BookmarkFlowable(bookmark_name, text, self._bookmark_pages))
                        # Add anchor to chapter title for TOC linking
                        chapter_text_with_anchor = f'<a name="{bookmark_name}"/>{text}'
                        elements.append(
                            self._create_paragraph(
                                chapter_text_with_anchor, styles["chapter-title"]
                            )
                        )
                        logger.debug(
                            f"PDFGenerator: Added bookmark anchor '{bookmark_name}' for chapter: {text}"
                        )
                    else:
                        # Fallback: no bookmark found (shouldn't happen with pre-scan)
                        elements.append(self._create_paragraph(text, styles["chapter-title"]))
                        logger.warning(f"PDFGenerator: No pre-scanned bookmark for chapter: {text}")
                processed_elements.add(child_id)

            elif element_type == "p":
                elements.extend(self._process_paragraph_element(child, styles))
                processed_elements.add(child_id)

            elif element_type == "div":
                div_elements = self._process_div_element(child, styles, processed_elements)
                elements.extend(div_elements)
                processed_elements.add(child_id)

                for descendant in child.find_all():
                    processed_elements.add(id(descendant))

        # Page numbers are now handled by the page template footer
        return elements

    def _process_paragraph_element(self, p_element, styles) -> list:
        """Process paragraph elements with styling."""
        classes = p_element.get("class", [])
        text = self._extract_formatted_text(p_element)

        if "story-text" in classes:
            return [self._create_paragraph(text, styles["story-text"])]
        elif "dialogue" in classes:
            return [self._create_paragraph(text, styles["dialogue"])]
        elif "emphasis" in classes:
            return [self._create_paragraph(text, styles["emphasis"])]
        else:
            return [self._create_paragraph(text, styles["story-text"])]

    def _process_div_element(self, div_element, styles, processed_elements: set = None) -> list:
        """Process div elements including images, quotes, and breaks."""
        elements = []
        classes = div_element.get("class", [])

        if processed_elements is None:
            processed_elements = set()

        # Handle page breaks
        if "page-break" in classes:
            elements.append(PageBreak())
            return elements

        if "story-break" in classes:
            text = div_element.get_text().strip()
            elements.append(Spacer(1, 0.4 * 72))
            elements.append(self._create_paragraph(text, styles["story-break"]))
            elements.append(Spacer(1, 0.4 * 72))

        elif "quote-box" in classes:
            # Keep quote boxes together on one page (don't split across pages)
            quote_elements = []
            text = self._extract_formatted_text(div_element)
            quote_elements.append(self._create_paragraph(text, styles["quote-box"]))
            # Wrap in KeepTogether to prevent splitting across pages
            elements.append(KeepTogether(quote_elements))

        elif any(poem_class in classes for poem_class in self.POEM_CLASSES):
            # Keep poem boxes together on one page (don't split across pages)
            poem_elements = []

            # Add spacer before poem box to prevent overlapping
            poem_elements.append(Spacer(1, 0.5 * 72))

            text = self._extract_poem_text(div_element)
            # Find the matching poem class and use appropriate style
            for poem_class in self.POEM_CLASSES:
                if poem_class in classes:
                    style = styles.get(poem_class, styles["poem-box"])
                    poem_elements.append(self._create_paragraph(text, style))
                    break

            # Add spacer after poem box to prevent overlapping
            poem_elements.append(Spacer(1, 0.5 * 72))

            # Wrap in KeepTogether to prevent splitting across pages
            elements.append(KeepTogether(poem_elements))

        elif any(formal_class in classes for formal_class in self.FORMAL_BOOK_CLASSES):
            if "front-cover-page" in classes:
                elements.extend(self._process_front_cover_page(div_element, styles))
            elif "back-cover-page" in classes:
                elements.extend(self._process_back_cover_page(div_element, styles))
            elif "explicit-title-page" in classes:
                elements.extend(self._process_explicit_title_page(div_element, styles))
            elif "publication-info" in classes:
                elements.extend(self._process_publication_info(div_element, styles))
            elif "title-page" in classes:
                elements.extend(self._process_title_page(div_element, styles))
            elif "table-of-contents" in classes:
                elements.extend(self._process_table_of_contents(div_element, styles))
            elif "preface" in classes:
                elements.extend(self._process_preface(div_element, styles))
            elif any(
                back_matter_class in classes for back_matter_class in self.BACK_MATTER_CLASSES
            ):
                elements.extend(self._process_back_matter(div_element, styles, classes))

        elif any(img_class in classes for img_class in self.IMAGE_CLASSES):
            elements.extend(self._process_image_element(div_element, styles, classes))

        elif "chapter-opener" in classes:
            for child in div_element.children:
                if isinstance(child, NavigableString):
                    continue

                child_id = id(child)
                if child_id in processed_elements:
                    continue

                if hasattr(child, "name") and child.name == "h2":
                    text = child.get_text().strip()
                    # Use pre-scanned bookmark for this chapter
                    bookmark_name = self._chapter_bookmarks.get(text)
                    if bookmark_name:
                        # Add PDF bookmark for outline navigation and page tracking
                        elements.append(BookmarkFlowable(bookmark_name, text, self._bookmark_pages))
                        # Add anchor to chapter title for TOC linking
                        chapter_text_with_anchor = f'<a name="{bookmark_name}"/>{text}'
                        elements.append(Spacer(1, 0.5 * 72))
                        elements.append(
                            self._create_paragraph(
                                chapter_text_with_anchor, styles["chapter-title"]
                            )
                        )
                        logger.debug(
                            f"PDFGenerator: Added bookmark anchor '{bookmark_name}' for chapter: {text}"
                        )
                    else:
                        # Fallback: no bookmark found (shouldn't happen with pre-scan)
                        elements.append(Spacer(1, 0.5 * 72))
                        elements.append(self._create_paragraph(text, styles["chapter-title"]))
                        logger.warning(f"PDFGenerator: No pre-scanned bookmark for chapter: {text}")
                    processed_elements.add(child_id)

        return elements

    def _process_image_element(self, div_element, styles, classes) -> list:
        """Process image elements with clear, simple, and adaptable handling."""
        elements: list[Any] = []
        pdf_config = config.style.pdf

        image_reference = self._extract_image_reference(div_element)
        if not image_reference:
            return elements

        image_path = self._find_image_file(image_reference)
        if not image_path:
            logger.warning(f"PDFGenerator: Cannot find image: {image_reference}")
            return elements

        max_width, max_height = self._get_image_dimensions(classes, pdf_config)

        caption = self._extract_image_caption(div_element)
        caption_height = 0
        if caption:
            caption_height = pdf_config.caption_font_size + 20

        available_height = (
            max_height
            - caption_height
            - pdf_config.image_space_before
            - pdf_config.image_space_after
        )
        if available_height < max_height * 0.3:
            available_height = max_height * 0.7
            caption_height = max_height * 0.3

        img_width, img_height = self._calculate_image_size(
            str(image_path), max_width, available_height
        )

        image_element = self._create_image_element(image_path, img_width, img_height)
        if not image_element:
            return elements

        image_section = [
            Spacer(1, pdf_config.image_space_before),
            image_element,
        ]
        if caption:
            image_section.append(self._create_paragraph(caption, styles["caption"]))
        image_section.append(Spacer(1, pdf_config.image_space_after))
        elements.append(KeepTogether(image_section))

        logger.info(
            f"PDFGenerator: Successfully added image {image_reference} ({img_width:.1f}x{img_height:.1f}) with caption as KeepTogether unit"
        )
        return elements

    # Removed: _extract_all_image_references and _clean_html_content
    # Now using BookContentProcessor.extract_image_references() and clean_html_content()

    def _extract_image_reference(self, div_element) -> str:
        """Extract image reference using pre-extracted mapping."""
        root = div_element
        while root.parent:
            root = root.parent

        all_image_divs = root.find_all("div", class_=self.IMAGE_CLASSES)

        current_image_index = None
        for i, img_div in enumerate(all_image_divs):
            if img_div == div_element:
                current_image_index = i
                break

        if current_image_index is not None and current_image_index in self._image_reference_map:
            image_ref = self._image_reference_map[current_image_index]
            logger.debug(
                f"PDFGenerator: Using pre-extracted reference {current_image_index}: '{image_ref}'"
            )
            return image_ref

        logger.warning(
            f"PDFGenerator: Could not find pre-extracted reference for image {current_image_index}"
        )

        # Try to find <img> tag with src attribute (standard HTML)
        img_tag = div_element.find("img")
        if img_tag and img_tag.get("src"):
            src_content = img_tag.get("src").strip()
            if src_content:
                logger.debug(f"PDFGenerator: Found img src: {src_content}")
                return src_content

        # Fallback to old <image> tag format
        image_tag = div_element.find("image")
        if image_tag:
            text_content = image_tag.get_text().strip()
            if text_content:
                return text_content

        logger.warning(
            "PDFGenerator: Empty image reference - no pre-extracted or fallback content found"
        )
        return ""

    def _find_image_file(self, image_reference: str) -> Path | None:
        """Find the actual image file from reference with flexible path resolution."""
        search_paths = [
            Path(image_reference) if Path(image_reference).is_absolute() else None,
            self.output_dir / image_reference,
            Path.cwd() / image_reference,
            self.output_dir / "images" / image_reference,
            self.output_dir.parent / "images" / image_reference,
        ]

        for path in search_paths:
            if path and path.exists() and path.is_file():
                logger.info(f"PDFGenerator: Found image at {path}")
                return path

        attempted_paths = [str(p) for p in search_paths if p]
        logger.warning(
            f"PDFGenerator: Image '{image_reference}' not found. Tried: {attempted_paths}"
        )
        return None

    def _get_image_dimensions(self, classes: list, pdf_config) -> tuple[float, float]:
        """Get max image dimensions based on image type and configuration.

        All dimensions are constrained to fit within the available frame space.
        """
        if "image-full-page" in classes:
            max_width = pdf_config.full_page_image_width
            max_height = pdf_config.full_page_image_height
        elif "image-chapter-opener" in classes:
            max_width = pdf_config.image_width * 1.2
            max_height = pdf_config.image_height * 1.2
        elif "image-inline-left" in classes or "image-inline-right" in classes:
            max_width = pdf_config.image_width * 0.8
            max_height = pdf_config.image_height * 0.8
        else:
            max_width = pdf_config.image_width
            max_height = pdf_config.image_height

        # Constrain to available frame dimensions to prevent "too large" errors
        max_width = min(max_width, self._available_width)
        max_height = min(max_height, self._available_height)

        return max_width, max_height

    def _calculate_cover_image_size(
        self, image_path: Path, max_width: float, max_height: float
    ) -> tuple[float, float]:
        """Calculate optimal image size that fits within bounds while maintaining aspect ratio."""
        try:
            from PIL import Image

            with Image.open(image_path) as pil_img:
                original_width, original_height = pil_img.size

            # Calculate scaling factor to fit within bounds
            width_scale = max_width / original_width
            height_scale = max_height / original_height
            scale_factor = min(width_scale, height_scale)

            # Apply scaling
            new_width = original_width * scale_factor
            new_height = original_height * scale_factor

            return new_width, new_height

        except Exception as e:
            logger.warning(f"PDFGenerator: Failed to calculate image size for {image_path}: {e}")
            # Fallback to max dimensions
            return max_width, max_height

    def _create_image_element(
        self, image_path: Path, width: float, height: float
    ) -> RLImage | None:
        """Create ReportLab image element with error handling."""
        try:
            img = RLImage(str(image_path))
            img.drawWidth = width
            img.drawHeight = height
            return img
        except Exception as e:
            logger.warning(f"PDFGenerator: Failed to create image element for {image_path}: {e}")
            return None

    def _extract_image_caption(self, div_element) -> str:
        """Extract caption text from image div element."""
        caption_div = div_element.find("div", class_="caption")
        if caption_div:
            return caption_div.get_text().strip()
        return ""

    def _extract_formatted_text(self, element) -> str:
        """Extract and format text from HTML element for ReportLab."""
        pdf_config = config.style.pdf
        text = ""

        for child in element.children:
            if isinstance(child, NavigableString):
                text += str(child)
            elif child.name == "br":
                # Convert HTML line breaks to ReportLab line breaks
                text += "<br/>"
            elif child.name == "span":
                span_classes = child.get("class", [])
                span_text = child.get_text()

                if "drop-cap" in span_classes and pdf_config.use_drop_caps:
                    drop_cap_size = pdf_config.body_font_size * 3
                    text += f'<font size="{drop_cap_size}" name="{pdf_config.title_font}">{span_text}</font>'
                elif "highlight" in span_classes:
                    text += f'<font name="{pdf_config.heading_font}" color="{pdf_config.accent_color}">{span_text}</font>'
                else:
                    text += span_text
            elif child.name in ["b", "strong"]:
                text += f'<font name="{pdf_config.heading_font}">{child.get_text()}</font>'
            elif child.name in ["i", "em"]:
                text += f"<i>{child.get_text()}</i>"
            else:
                text += child.get_text()

        # Check if this is a poem element - preserve line structure for poems
        element_classes = element.get("class", []) if hasattr(element, "get") else []
        is_poem = any(cls in element_classes for cls in self.POEM_CLASSES)

        if is_poem:
            # For poems, preserve line breaks and only normalize excessive whitespace
            text = re.sub(r"[ \t]+", " ", text)  # Only collapse spaces and tabs
            text = re.sub(r"\n\s*\n", "\n", text)  # Remove empty lines but keep single newlines
            text = text.strip()
        else:
            # For regular text, collapse all whitespace as before
            text = re.sub(r"\s+", " ", text.strip())

        text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
        return text

    def _extract_poem_text(self, element) -> str:
        """Extract text from poem elements with proper line break preservation."""
        pdf_config = config.style.pdf
        lines = []
        current_line = ""
        formatting_stack = []  # Track nested formatting (italic, bold, etc.)

        def get_current_formatting():
            """Get opening and closing tags for current formatting state."""
            opening = "".join(formatting_stack)
            closing = "".join(reversed([tag.replace("<", "</") for tag in formatting_stack]))
            return opening, closing

        def process_element(elem):
            nonlocal current_line
            for child in elem.children:
                if isinstance(child, NavigableString):
                    current_line += str(child).strip()
                elif child.name == "br":
                    # Close any open formatting tags before line break
                    _, closing = get_current_formatting()
                    current_line += closing
                    # End current line and start new one (preserve blank lines for stanza breaks)
                    lines.append(current_line.strip())
                    # Reopen formatting tags on new line
                    opening, _ = get_current_formatting()
                    current_line = opening
                elif child.name == "span":
                    span_classes = child.get("class", [])
                    span_text = child.get_text().strip()

                    if "drop-cap" in span_classes and pdf_config.use_drop_caps:
                        drop_cap_size = pdf_config.body_font_size * 3
                        current_line += f'<font size="{drop_cap_size}" name="{pdf_config.title_font}">{span_text}</font>'
                    elif "highlight" in span_classes:
                        current_line += f'<font name="{pdf_config.heading_font}" color="{pdf_config.accent_color}">{span_text}</font>'
                    else:
                        current_line += span_text
                elif child.name in ["b", "strong"]:
                    # Recursively process bold to preserve line breaks
                    bold_tag = f'<font name="{pdf_config.heading_font}">'
                    formatting_stack.append(bold_tag)
                    current_line += bold_tag
                    process_element(child)
                    current_line += "</font>"
                    formatting_stack.pop()
                elif child.name in ["i", "em"]:
                    # Recursively process italic to preserve line breaks
                    formatting_stack.append("<i>")
                    current_line += "<i>"
                    process_element(child)
                    current_line += "</i>"
                    formatting_stack.pop()
                else:
                    # Recursively process nested elements
                    process_element(child)

        process_element(element)

        # Add any remaining content as the last line
        if current_line.strip():
            lines.append(current_line.strip())

        # Remove beginning and ending quotes from poem lines
        if lines:
            # Strip opening quotes from first line (before any HTML tags)
            first_line = lines[0]
            for quote_char in ['"', "'", '"', '"', """, """]:
                if first_line.lstrip().startswith(quote_char):
                    # Find the position after any opening tags
                    stripped = first_line.lstrip()
                    # Remove the quote character
                    stripped = stripped[len(quote_char) :]
                    # Preserve any leading whitespace and tags
                    lines[0] = first_line[: len(first_line) - len(first_line.lstrip())] + stripped
                    break

            # Strip closing quotes from last line (after any HTML tags)
            last_line = lines[-1]
            for quote_char in ['"', "'", '"', '"', """, """]:
                if last_line.rstrip().endswith(quote_char):
                    # Find the position before any closing tags
                    stripped = last_line.rstrip()
                    # Remove the quote character
                    stripped = stripped[: -len(quote_char)]
                    # Preserve any trailing whitespace and tags
                    lines[-1] = stripped + last_line[len(last_line.rstrip()) :]
                    break

        # Join lines with ReportLab line breaks
        poem_text = "<br/>".join(lines) if lines else ""

        # Clean up HTML entities
        poem_text = poem_text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")

        return poem_text

    def _create_paragraph(self, text: str, style) -> Paragraph:
        """Create a Paragraph with graceful error handling."""
        try:
            return Paragraph(text, style)
        except Exception as e:
            logger.warning(f"PDFGenerator: Paragraph creation failed, using plain text: {e}")
            plain_text = re.sub(r"<[^>]+>", "", text)
            try:
                return Paragraph(plain_text, style)
            except Exception:
                return Paragraph("[Text formatting error]", style)

    def _create_fallback_pdf(self, pdf_path: Path, html_content: str) -> None:
        """Create a simple fallback PDF if main generation fails."""
        try:
            doc = SimpleDocTemplate(str(pdf_path))
            styles = getSampleStyleSheet()
            story = []

            soup = BeautifulSoup(html_content, "html.parser")
            plain_text = soup.get_text()

            paragraphs = plain_text.split("\n\n")
            for para in paragraphs:
                if para.strip():
                    story.append(Paragraph(para.strip(), styles["Normal"]))
                    story.append(Spacer(1, 12))

            doc.build(story)
            logger.info(f"PDFGenerator: Fallback PDF created: {pdf_path}")
        except Exception as e:
            logger.error(f"PDFGenerator: Even fallback PDF creation failed: {e}")

    def _create_styles(self) -> dict:
        """Create comprehensive styles using config settings."""
        base_styles = getSampleStyleSheet()
        pdf_config = config.style.pdf
        styles = {}

        # Helper variables with fallbacks to constants
        title_font = pdf_config.title_font
        heading_font = pdf_config.heading_font
        body_font = pdf_config.body_font
        story_font = pdf_config.story_font
        caption_font = pdf_config.caption_font

        body_font_size = pdf_config.body_font_size

        title_color = pdf_config.title_color
        chapter_color = pdf_config.chapter_color
        body_color = pdf_config.body_color
        caption_color = pdf_config.caption_color

        title_space_after = pdf_config.title_space_after
        paragraph_space_after = pdf_config.paragraph_space_after
        line_height_multiplier = pdf_config.line_height_multiplier

        styles["book-title"] = ParagraphStyle(
            "BookTitle",
            parent=base_styles["Normal"],
            fontName=pdf_config.title_font,
            fontSize=pdf_config.title_font_size,
            leading=pdf_config.title_font_size * pdf_config.line_height_multiplier,
            alignment=TA_CENTER,
            textColor=HexColor(pdf_config.title_color),
            spaceAfter=pdf_config.title_space_after,
            spaceBefore=pdf_config.title_space_after,
        )

        styles["chapter-title"] = ParagraphStyle(
            "ChapterTitle",
            parent=base_styles["Normal"],
            fontName=pdf_config.heading_font,
            fontSize=pdf_config.chapter_font_size,
            leading=pdf_config.chapter_font_size * pdf_config.line_height_multiplier,
            alignment=TA_CENTER,
            textColor=HexColor(pdf_config.chapter_color),
            spaceAfter=pdf_config.chapter_space_after,
            spaceBefore=pdf_config.chapter_space_before,
        )

        styles["story-text"] = ParagraphStyle(
            "StoryText",
            parent=base_styles["Normal"],
            fontName=pdf_config.story_font,
            fontSize=pdf_config.body_font_size,
            leading=pdf_config.body_font_size * pdf_config.line_height_multiplier,
            alignment=TA_JUSTIFY if pdf_config.justify_text else TA_LEFT,
            leftIndent=pdf_config.body_left_indent,
            rightIndent=pdf_config.body_right_indent,
            spaceAfter=pdf_config.paragraph_space_after,
            firstLineIndent=pdf_config.first_line_indent,
            textColor=HexColor(pdf_config.body_color),
        )

        styles["dialogue"] = ParagraphStyle(
            "Dialogue",
            parent=base_styles["Normal"],
            fontName=pdf_config.story_font,
            fontSize=pdf_config.quote_font_size,
            leading=pdf_config.quote_font_size * pdf_config.line_height_multiplier,
            alignment=TA_LEFT,
            leftIndent=pdf_config.dialogue_left_indent,
            spaceAfter=pdf_config.paragraph_space_after,
            textColor=HexColor(pdf_config.quote_color),
        )

        styles["emphasis"] = ParagraphStyle(
            "Emphasis",
            parent=base_styles["Normal"],
            fontName=pdf_config.heading_font,
            fontSize=pdf_config.body_font_size + 2,
            leading=(pdf_config.body_font_size + 2) * pdf_config.line_height_multiplier,
            alignment=TA_CENTER,
            textColor=HexColor(pdf_config.accent_color),
            spaceAfter=pdf_config.paragraph_space_after,
            spaceBefore=pdf_config.paragraph_space_after,
        )

        styles["caption"] = ParagraphStyle(
            "Caption",
            parent=base_styles["Normal"],
            fontName=pdf_config.caption_font,
            fontSize=pdf_config.caption_font_size,
            leading=pdf_config.caption_font_size * pdf_config.line_height_multiplier,
            alignment=TA_CENTER,
            textColor=HexColor(pdf_config.caption_color),
            spaceAfter=pdf_config.paragraph_space_after,
        )

        styles["quote-box"] = ParagraphStyle(
            "QuoteBox",
            parent=base_styles["Normal"],
            fontName=pdf_config.story_font,
            fontSize=pdf_config.quote_font_size,
            leading=pdf_config.quote_font_size * pdf_config.line_height_multiplier,
            alignment=TA_CENTER,
            leftIndent=1.0 * 72,
            rightIndent=1.0 * 72,
            borderWidth=2,
            borderColor=HexColor(pdf_config.accent_color),
            borderPadding=0.4 * 72,  # Increased padding
            textColor=HexColor(pdf_config.quote_color),
            spaceAfter=pdf_config.paragraph_space_after * 2,  # More space after
            spaceBefore=pdf_config.paragraph_space_after * 2,  # More space before
        )

        styles["page-number"] = ParagraphStyle(
            "PageNumber",
            parent=base_styles["Normal"],
            fontName=pdf_config.body_font,
            fontSize=pdf_config.page_number_font_size,
            alignment=TA_CENTER,
            textColor=HexColor(pdf_config.caption_color),
        )

        styles["story-break"] = ParagraphStyle(
            "StoryBreak",
            parent=base_styles["Normal"],
            fontName=pdf_config.heading_font,
            fontSize=pdf_config.body_font_size + 4,
            alignment=TA_CENTER,
            textColor=HexColor(pdf_config.accent_color),
            spaceAfter=pdf_config.paragraph_space_after,
            spaceBefore=pdf_config.paragraph_space_after,
        )

        # Poem and rhythmic content styles (signature Cassie series elements)
        # Using neutral colors that work in both light and dark modes
        body_font_size = pdf_config.body_font_size
        paragraph_space = pdf_config.paragraph_space_after

        styles["poem-box"] = ParagraphStyle(
            "PoemBox",
            parent=base_styles["Normal"],
            fontName=pdf_config.story_font,
            fontSize=body_font_size,
            leading=body_font_size * 1.6,  # Extra line spacing for poems
            alignment=TA_CENTER,
            leftIndent=0.8 * 72,  # Indent for visual prominence
            rightIndent=0.8 * 72,
            borderWidth=2,
            borderColor=HexColor(pdf_config.poem_border_color),
            borderPadding=0.5 * 72,  # Generous padding
            backColor=HexColor(pdf_config.background_accent),
            textColor=HexColor(pdf_config.poem_text_color),
            spaceAfter=paragraph_space * 2,
            spaceBefore=paragraph_space * 2,
        )

        styles["poem-verse"] = ParagraphStyle(
            "PoemVerse",
            parent=base_styles["Normal"],
            fontName=pdf_config.story_font,
            fontSize=body_font_size,
            leading=body_font_size * 1.5,
            alignment=TA_CENTER,
            leftIndent=1.0 * 72,
            rightIndent=1.0 * 72,
            textColor=HexColor(pdf_config.chapter_color),
            spaceAfter=paragraph_space,
        )

        styles["chant-box"] = ParagraphStyle(
            "ChantBox",
            parent=base_styles["Normal"],
            fontName=pdf_config.heading_font,  # Bold font for chants
            fontSize=body_font_size,
            leading=body_font_size * 1.4,
            alignment=TA_CENTER,
            leftIndent=0.5 * 72,
            rightIndent=0.5 * 72,
            borderWidth=2,
            borderColor=HexColor(pdf_config.chant_border_color),
            borderPadding=0.3 * 72,
            backColor=HexColor(pdf_config.background_accent),
            textColor=HexColor(pdf_config.chant_text_color),
            spaceAfter=paragraph_space * 2,
            spaceBefore=paragraph_space * 2,
        )

        styles["song-lyrics"] = ParagraphStyle(
            "SongLyrics",
            parent=base_styles["Normal"],
            fontName=pdf_config.caption_font,  # Italic font for songs
            fontSize=body_font_size,
            leading=body_font_size * 1.6,
            alignment=TA_CENTER,
            leftIndent=1.2 * 72,
            rightIndent=1.2 * 72,
            borderWidth=2,
            borderColor=HexColor(pdf_config.song_border_color),
            borderPadding=0.4 * 72,
            backColor=HexColor(pdf_config.background_accent),
            textColor=HexColor(pdf_config.song_text_color),
            spaceAfter=paragraph_space * 2,
            spaceBefore=paragraph_space * 2,
        )

        # Formal book element styles
        styles["cover-title"] = ParagraphStyle(
            "CoverTitle",
            parent=base_styles["Normal"],
            fontName=title_font,
            fontSize=pdf_config.cover_title_font_size,
            leading=pdf_config.cover_title_font_size * 1.2,
            alignment=TA_CENTER,
            textColor=HexColor(pdf_config.cover_title_color),
            spaceAfter=title_space_after * 1.5,
            spaceBefore=title_space_after,
        )

        styles["cover-subtitle"] = ParagraphStyle(
            "CoverSubtitle",
            parent=base_styles["Normal"],
            fontName=heading_font,
            fontSize=pdf_config.cover_subtitle_font_size,
            leading=pdf_config.cover_subtitle_font_size * 1.2,
            alignment=TA_CENTER,
            textColor=HexColor(chapter_color),
            spaceAfter=paragraph_space_after,
        )

        styles["cover-author"] = ParagraphStyle(
            "CoverAuthor",
            parent=base_styles["Normal"],
            fontName=heading_font,
            fontSize=pdf_config.cover_author_font_size,
            leading=pdf_config.cover_author_font_size * 1.2,
            alignment=TA_CENTER,
            textColor=HexColor(body_color),
            spaceAfter=paragraph_space_after * 2,
        )

        styles["cover-publisher"] = ParagraphStyle(
            "CoverPublisher",
            parent=base_styles["Normal"],
            fontName=body_font,
            fontSize=pdf_config.cover_publisher_font_size,
            leading=pdf_config.cover_publisher_font_size * 1.2,
            alignment=TA_CENTER,
            textColor=HexColor(caption_color),
            spaceAfter=paragraph_space_after,
        )

        styles["cover-logo"] = ParagraphStyle(
            "CoverLogo",
            parent=base_styles["Normal"],
            alignment=TA_CENTER,
            spaceAfter=paragraph_space_after * 2,
        )

        styles["toc-title"] = ParagraphStyle(
            "TOCTitle",
            parent=base_styles["Normal"],
            fontName=title_font,
            fontSize=pdf_config.toc_title_font_size,
            leading=pdf_config.toc_title_font_size * 1.2,
            alignment=TA_CENTER,
            textColor=HexColor(pdf_config.toc_color),
            spaceAfter=paragraph_space_after * 2,
            spaceBefore=paragraph_space_after,
        )

        styles["toc-entry"] = ParagraphStyle(
            "TOCEntry",
            parent=base_styles["Normal"],
            fontName=body_font,
            fontSize=pdf_config.toc_entry_font_size,
            leading=pdf_config.toc_entry_font_size * 1.3,
            alignment=TA_LEFT,
            textColor=HexColor(body_color),
            spaceAfter=paragraph_space_after * 0.5,
            leftIndent=0.5 * 72,
        )

        styles["preface-title"] = ParagraphStyle(
            "PrefaceTitle",
            parent=base_styles["Normal"],
            fontName=heading_font,
            fontSize=pdf_config.preface_title_font_size,
            leading=pdf_config.preface_title_font_size * 1.2,
            alignment=TA_CENTER,
            textColor=HexColor(pdf_config.preface_color),
            spaceAfter=paragraph_space_after * 1.5,
            spaceBefore=paragraph_space_after,
        )

        styles["preface-text"] = ParagraphStyle(
            "PrefaceText",
            parent=base_styles["Normal"],
            fontName=body_font,
            fontSize=pdf_config.preface_body_font_size,
            leading=pdf_config.preface_body_font_size * line_height_multiplier,
            alignment=TA_JUSTIFY if pdf_config.justify_text else TA_LEFT,
            textColor=HexColor(body_color),
            spaceAfter=paragraph_space_after,
        )

        styles["index-title"] = ParagraphStyle(
            "IndexTitle",
            parent=base_styles["Normal"],
            fontName=title_font,
            fontSize=pdf_config.preface_title_font_size,
            leading=pdf_config.preface_title_font_size * 1.2,
            alignment=TA_CENTER,
            textColor=HexColor(pdf_config.index_color),
            spaceAfter=paragraph_space_after * 1.5,
            spaceBefore=paragraph_space_after,
        )

        styles["index-entry"] = ParagraphStyle(
            "IndexEntry",
            parent=base_styles["Normal"],
            fontName=body_font,
            fontSize=pdf_config.index_entry_font_size,
            leading=pdf_config.index_entry_font_size * 1.2,
            alignment=TA_LEFT,
            textColor=HexColor(body_color),
            spaceAfter=paragraph_space_after * 0.3,
            leftIndent=0.25 * 72,
        )

        # Specific poem type styles with distinct colors and formatting
        styles["haiku-box"] = ParagraphStyle(
            "HaikuBox",
            parent=base_styles["Normal"],
            fontName=story_font,
            fontSize=body_font_size,
            leading=body_font_size * 1.8,  # Extra spacing for haikus
            alignment=TA_CENTER,
            leftIndent=1.0 * 72,
            rightIndent=1.0 * 72,
            borderWidth=1,
            borderColor=HexColor(pdf_config.haiku_border_color),  # Dark blue
            borderPadding=0.4 * 72,
            textColor=HexColor(pdf_config.haiku_text_color),
            spaceAfter=paragraph_space_after * 4,  # 2 line padding after
            spaceBefore=paragraph_space_after * 4,  # 2 line padding before
        )

        styles["limerick-box"] = ParagraphStyle(
            "LimerickBox",
            parent=base_styles["Normal"],
            fontName=story_font,
            fontSize=body_font_size,
            leading=body_font_size * 1.6,  # Bouncy rhythm spacing
            alignment=TA_CENTER,
            leftIndent=0.8 * 72,
            rightIndent=0.8 * 72,
            borderWidth=2,
            borderColor=HexColor(pdf_config.limerick_border_color),  # Purple
            borderPadding=0.5 * 72,
            textColor=HexColor(pdf_config.limerick_text_color),
            spaceAfter=paragraph_space_after * 4,  # 2 line padding after
            spaceBefore=paragraph_space_after * 4,  # 2 line padding before
        )

        styles["cinquain-box"] = ParagraphStyle(
            "CinquainBox",
            parent=base_styles["Normal"],
            fontName=story_font,
            fontSize=body_font_size,
            leading=body_font_size * 1.7,  # Progressive build spacing
            alignment=TA_CENTER,
            leftIndent=1.2 * 72,
            rightIndent=1.2 * 72,
            borderWidth=1,
            borderColor=HexColor(pdf_config.cinquain_border_color),  # Orange-red
            borderPadding=0.6 * 72,
            textColor=HexColor(pdf_config.cinquain_text_color),
            spaceAfter=paragraph_space_after * 4,  # 2 line padding after
            spaceBefore=paragraph_space_after * 4,  # 2 line padding before
        )

        # Front Cover styles - vibrant blue colors for maximum contrast and visibility
        # Using blue/cyan tones that provide excellent contrast on most backgrounds
        styles["front-cover-title"] = ParagraphStyle(
            "FrontCoverTitle",
            parent=base_styles["Normal"],
            fontName=title_font,
            fontSize=pdf_config.front_cover_title_font_size,
            leading=pdf_config.front_cover_title_font_size * 1.3,
            alignment=TA_CENTER,
            textColor=HexColor("#0369A1"),  # Deep blue for strong presence and high contrast
            spaceAfter=title_space_after * 0.5,
            spaceBefore=title_space_after * 0.3,
            borderWidth=0,
            borderPadding=8,
        )

        styles["front-cover-subtitle"] = ParagraphStyle(
            "FrontCoverSubtitle",
            parent=base_styles["Normal"],
            fontName=body_font,
            fontSize=pdf_config.front_cover_subtitle_font_size,
            leading=pdf_config.front_cover_subtitle_font_size * 1.3,
            alignment=TA_CENTER,
            textColor=HexColor("#0284C7"),  # Rich cyan-blue for subtitle, complements title
            spaceAfter=paragraph_space_after,
        )

        styles["front-cover-author"] = ParagraphStyle(
            "FrontCoverAuthor",
            parent=base_styles["Normal"],
            fontName=body_font,
            fontSize=pdf_config.front_cover_author_font_size,
            leading=pdf_config.front_cover_author_font_size * 1.3,
            alignment=TA_CENTER,
            textColor=HexColor("#0EA5E9"),  # Vibrant cyan-blue matching title
            spaceAfter=paragraph_space_after * 0.5,
        )

        styles["front-cover-publisher"] = ParagraphStyle(
            "FrontCoverPublisher",
            parent=base_styles["Normal"],
            fontName=body_font,
            fontSize=pdf_config.front_cover_publisher_font_size,
            leading=pdf_config.front_cover_publisher_font_size * 1.3,
            alignment=TA_CENTER,
            textColor=HexColor("#7DD3FC"),  # Light sky blue for publisher
            spaceAfter=paragraph_space_after * 0.3,
        )

        # Back Cover styles
        styles["back-cover-description"] = ParagraphStyle(
            "BackCoverDescription",
            parent=base_styles["Normal"],
            fontName=body_font,
            fontSize=pdf_config.back_cover_description_font_size,
            leading=pdf_config.back_cover_description_font_size * 1.4,
            alignment=TA_CENTER,
            textColor=HexColor("#333333"),
            spaceAfter=paragraph_space_after * 0.3,  # Minimal to fit on one page
            leftIndent=1.0 * inch,  # Padding from left edge
            rightIndent=1.0 * inch,  # Padding from right edge
            borderWidth=0,
            borderPadding=12,
        )

        styles["back-cover-publisher"] = ParagraphStyle(
            "BackCoverPublisher",
            parent=base_styles["Normal"],
            fontName=body_font,
            fontSize=pdf_config.back_cover_publisher_font_size,
            leading=pdf_config.back_cover_publisher_font_size * 1.2,
            alignment=TA_LEFT,
            textColor=HexColor("#333333"),
            spaceAfter=paragraph_space_after * 0.2,  # Minimal spacing
            leftIndent=1.0 * inch,  # Padding from left edge
            rightIndent=1.0 * inch,  # Padding from right edge
        )

        styles["back-cover-location"] = ParagraphStyle(
            "BackCoverLocation",
            parent=base_styles["Normal"],
            fontName=body_font,
            fontSize=pdf_config.back_cover_location_font_size,
            leading=pdf_config.back_cover_location_font_size * 1.2,
            alignment=TA_LEFT,
            textColor=HexColor("#666666"),
            spaceAfter=paragraph_space_after * 0.2,  # Minimal spacing
            leftIndent=1.0 * inch,  # Padding from left edge
            rightIndent=1.0 * inch,  # Padding from right edge
        )

        styles["isbn"] = ParagraphStyle(
            "ISBN",
            parent=base_styles["Normal"],
            fontName=body_font,
            fontSize=pdf_config.isbn_font_size,
            leading=pdf_config.isbn_font_size * 1.2,
            alignment=TA_RIGHT,
            textColor=HexColor("#666666"),
            spaceAfter=paragraph_space_after * 0.2,  # Minimal spacing
            leftIndent=1.0 * inch,  # Padding from left edge
            rightIndent=1.0 * inch,  # Padding from right edge
        )

        # Explicit Title Page styles
        styles["title-page-title"] = ParagraphStyle(
            "TitlePageTitle",
            parent=base_styles["Normal"],
            fontName=title_font,
            fontSize=pdf_config.title_page_title_font_size,
            leading=pdf_config.title_page_title_font_size * 1.2,
            alignment=TA_CENTER,
            textColor=HexColor(title_color),
            spaceAfter=title_space_after,
        )

        styles["title-page-subtitle"] = ParagraphStyle(
            "TitlePageSubtitle",
            parent=base_styles["Normal"],
            fontName=body_font,
            fontSize=pdf_config.title_page_subtitle_font_size,
            leading=pdf_config.title_page_subtitle_font_size * 1.2,
            alignment=TA_CENTER,
            textColor=HexColor(pdf_config.subtitle_color),
            spaceAfter=paragraph_space_after * 2,
        )

        styles["title-page-author"] = ParagraphStyle(
            "TitlePageAuthor",
            parent=base_styles["Normal"],
            fontName=body_font,
            fontSize=pdf_config.title_page_author_font_size,
            leading=pdf_config.title_page_author_font_size * 1.2,
            alignment=TA_CENTER,
            textColor=HexColor(body_color),
            spaceAfter=paragraph_space_after,
        )

        styles["title-page-publisher"] = ParagraphStyle(
            "TitlePagePublisher",
            parent=base_styles["Normal"],
            fontName=body_font,
            fontSize=pdf_config.publication_info_font_size,
            leading=pdf_config.title_page_publisher_font_size * 1.2,
            alignment=TA_CENTER,
            textColor=HexColor(caption_color),
            spaceAfter=paragraph_space_after,
        )

        # Powered by FableFlow styles
        styles["powered-by-text"] = ParagraphStyle(
            "PoweredByText",
            parent=base_styles["Normal"],
            fontName=caption_font,  # Italic
            fontSize=14,
            leading=14 * 1.2,
            alignment=TA_CENTER,
            textColor=HexColor("#666666"),
            spaceAfter=paragraph_space_after * 0.5,
        )

        # Publication Info styles
        styles["publication-info"] = ParagraphStyle(
            "PublicationInfo",
            parent=base_styles["Normal"],
            fontName=body_font,
            fontSize=pdf_config.publication_info_font_size,
            leading=pdf_config.publication_info_font_size * 1.2,
            alignment=TA_CENTER,
            textColor=HexColor(body_color),
            spaceAfter=paragraph_space_after * 0.5,
        )

        # Publication Info sub-styles
        styles["pub-publisher"] = ParagraphStyle(
            "PubPublisher",
            parent=base_styles["Normal"],
            fontName=heading_font,
            fontSize=14,
            leading=14 * 1.2,
            alignment=TA_CENTER,
            textColor=HexColor(title_color),
            spaceAfter=paragraph_space_after * 0.3,
        )

        styles["pub-edition"] = ParagraphStyle(
            "PubEdition",
            parent=base_styles["Normal"],
            fontName=body_font,
            fontSize=12,
            leading=12 * 1.2,
            alignment=TA_CENTER,
            textColor=HexColor("#666666"),
            spaceAfter=paragraph_space_after * 0.3,
        )

        styles["pub-credits"] = ParagraphStyle(
            "PubCredits",
            parent=base_styles["Normal"],
            fontName=body_font,
            fontSize=11,
            leading=11 * 1.5,
            alignment=TA_CENTER,
            textColor=HexColor(body_color),
            spaceAfter=paragraph_space_after * 0.3,
        )

        styles["pub-copyright"] = ParagraphStyle(
            "PubCopyright",
            parent=base_styles["Normal"],
            fontName=body_font,
            fontSize=11,
            leading=11 * 1.5,
            alignment=TA_CENTER,
            textColor=HexColor("#666666"),
            spaceAfter=paragraph_space_after * 0.3,
        )

        styles["pub-isbn"] = ParagraphStyle(
            "PubISBN",
            parent=base_styles["Normal"],
            fontName=heading_font,
            fontSize=12,
            leading=12 * 1.2,
            alignment=TA_CENTER,
            textColor=HexColor(title_color),
            spaceAfter=paragraph_space_after * 0.3,
        )

        styles["pub-disclaimer"] = ParagraphStyle(
            "PubDisclaimer",
            parent=base_styles["Normal"],
            fontName=caption_font,  # Italic
            fontSize=10,
            leading=10 * 1.4,
            alignment=TA_CENTER,
            textColor=HexColor("#666666"),
            spaceAfter=paragraph_space_after * 0.3,
        )

        styles["isbn"] = ParagraphStyle(
            "ISBN",
            parent=base_styles["Normal"],
            fontName=body_font,
            fontSize=pdf_config.isbn_font_size,
            leading=pdf_config.isbn_font_size * 1.2,
            alignment=TA_CENTER,
            textColor=HexColor("#666666"),
            spaceAfter=paragraph_space_after * 0.5,
        )

        return styles

    def _calculate_image_size(
        self, image_path: str, max_width: float, max_height: float
    ) -> tuple[float, float]:
        try:
            from PIL import Image

            logger.info(f"PDFGenerator: Opening image file: {image_path}")
            with Image.open(image_path) as img:
                original_width, original_height = img.size
                logger.info(
                    f"PDFGenerator: Original image size: {original_width}x{original_height}"
                )

            aspect_ratio = original_width / original_height
            logger.info(f"PDFGenerator: Image aspect ratio: {aspect_ratio:.2f}")

            # Calculate available page height (from page config)
            pdf_config = config.style.pdf
            page_height = pdf_config.page_size[1]
            available_page_height = (
                page_height
                - pdf_config.margin_top
                - pdf_config.margin_bottom
                - 0.5 * 72  # Footer space reserved in _create_document
            )

            # Apply user-requested constraints: min 1/3, max 4/5 of available page height
            min_height = available_page_height * (1 / 3)  # 1/3 of page height
            max_height_constraint = available_page_height * (4 / 5)  # 4/5 of page height

            logger.info(
                f"PDFGenerator: Page height constraints - min: {min_height:.1f}, max: {max_height_constraint:.1f}"
            )

            # Reserve space for caption and footer
            caption_height = pdf_config.caption_font_size + 20
            footer_height = pdf_config.page_number_font_size + 20
            reserved_height = caption_height + footer_height + 40  # 40 points extra padding

            # Adjust max height to account for reserved space
            adjusted_max_height = max_height - reserved_height
            if adjusted_max_height < max_height * 0.3:  # If too little space left
                adjusted_max_height = max_height * 0.6  # Use 60% of max height

            # Ensure adjusted_max_height respects the maximum constraint
            adjusted_max_height = min(adjusted_max_height, max_height_constraint)

            if aspect_ratio > max_width / adjusted_max_height:
                width = max_width
                height = max_width / aspect_ratio
                logger.info(f"PDFGenerator: Width-limited sizing: {width:.1f}x{height:.1f}")
            else:
                height = adjusted_max_height
                width = adjusted_max_height * aspect_ratio
                logger.info(f"PDFGenerator: Height-limited sizing: {width:.1f}x{height:.1f}")

            # Apply minimum height constraint (never print as thumbnail)
            if height < min_height:
                logger.info(
                    f"PDFGenerator: Image height ({height:.1f}) below minimum ({min_height:.1f}), scaling up"
                )
                height = min_height
                width = min_height * aspect_ratio
                # If width exceeds max_width after scaling, scale down proportionally
                if width > max_width:
                    width = max_width
                    height = max_width / aspect_ratio
                    logger.info(
                        f"PDFGenerator: Width exceeded, adjusted to: {width:.1f}x{height:.1f}"
                    )

            # Apply maximum height constraint (never exceed 4/5 of page height)
            if height > max_height_constraint:
                logger.info(
                    f"PDFGenerator: Image height ({height:.1f}) exceeds maximum ({max_height_constraint:.1f}), scaling down"
                )
                height = max_height_constraint
                width = max_height_constraint * aspect_ratio
                if width > max_width:
                    width = max_width
                    height = max_width / aspect_ratio

            logger.info(f"PDFGenerator: Final image size: {width:.1f}x{height:.1f}")
            return width, height

        except Exception as e:
            logger.error(f"PDFGenerator: Error calculating image size for {image_path}: {e}")
            fallback_width = min(max_width * 0.7, 250)  # More conservative fallback
            fallback_height = min(max_height * 0.7, 150)
            logger.info(
                f"PDFGenerator: Using fallback image size: {fallback_width:.1f}x{fallback_height:.1f}"
            )
            return fallback_width, fallback_height

    def _process_title_page(self, div_element, styles) -> list:
        """Process title page elements."""
        elements = []
        elements.append(Spacer(1, 1.5 * 72))  # Top spacing

        for child in div_element.children:
            if isinstance(child, NavigableString):
                continue

            if hasattr(child, "name"):
                text = child.get_text().strip()
                if text:
                    # Use appropriate style based on content
                    if "title" in text.lower() or child.name == "h1":
                        elements.append(self._create_paragraph(text, styles["cover-title"]))
                    elif child.name == "h2":
                        elements.append(self._create_paragraph(text, styles["cover-subtitle"]))
                    else:
                        elements.append(self._create_paragraph(text, styles["preface-text"]))

        elements.append(PageBreak())  # New page after title page
        # Add invisible content to force blank page to exist
        elements.append(Paragraph("&nbsp;", styles.get("Normal", styles.get("body-text"))))
        elements.append(PageBreak())  # Move past the blank page
        return elements

    def _process_front_cover_page(self, div_element, styles) -> list:
        """Process front cover page with background image and text overlay.

        Regenerates the front cover HTML using BookStructureGenerator to ensure
        correct author attribution and consistent metadata.
        """
        from fable_flow.config import config

        elements = []

        # Switch to cover page template (minimal margins, no page numbers)
        elements.append(NextPageTemplate("cover"))

        # Regenerate front cover HTML with correct metadata (like EPUB does)
        logger.info("PDFGenerator: Regenerating front cover HTML with BookStructureGenerator")
        structure_gen = BookStructureGenerator(self.output_dir, self._book_metadata, format="pdf")
        fresh_html = structure_gen.generate_front_cover_html()

        # Parse the regenerated HTML
        fresh_soup = BeautifulSoup(fresh_html, "html.parser")
        cover_page = fresh_soup.find("div", class_="front-cover-page")

        # Try to load the front cover image as background
        front_cover_path = self.output_dir / "front_cover.png"
        if front_cover_path.exists():
            try:
                # Use maximized dimensions for cover with minimal padding
                # This makes the cover fill most of the page like a real book
                img_width, img_height = self._calculate_cover_image_size(
                    front_cover_path, self._cover_max_width, self._cover_max_height
                )

                background_image = RLImage(
                    str(front_cover_path), width=img_width, height=img_height
                )
                elements.append(background_image)

                # Use negative spacer based on actual image height to overlay text
                # Reduced spacing for tighter layout on cover page
                elements.append(Spacer(1, -img_height + (0.5 * 72)))

                # Extract text from the regenerated HTML (not old HTML)
                overlay_div = (
                    cover_page.find("div", class_="cover-text-overlay") if cover_page else None
                )
                if overlay_div:
                    # Reduced top spacing for tighter cover layout
                    elements.append(Spacer(1, 0.3 * 72))

                    for child in overlay_div.children:
                        if isinstance(child, NavigableString):
                            continue

                        if hasattr(child, "name"):
                            text = child.get_text().strip()
                            if not text:
                                continue

                            if child.name == "h1" and "front-cover-title" in child.get("class", []):
                                elements.append(
                                    self._create_paragraph(text, styles["front-cover-title"])
                                )
                                logger.info(f"PDFGenerator: Front cover title: {text}")
                            elif child.name == "h2" and "front-cover-subtitle" in child.get(
                                "class", []
                            ):
                                elements.append(
                                    self._create_paragraph(text, styles["front-cover-subtitle"])
                                )
                                logger.info(f"PDFGenerator: Front cover subtitle: {text}")
                            elif child.name == "p" and "front-cover-author" in child.get(
                                "class", []
                            ):
                                # Reduced spacing before author for tighter cover layout
                                elements.append(Spacer(1, 0.5 * 72))
                                elements.append(
                                    self._create_paragraph(text, styles["front-cover-author"])
                                )
                                logger.info(f"PDFGenerator: Front cover author: {text}")
                            elif child.name == "p" and "front-cover-publisher" in child.get(
                                "class", []
                            ):
                                # Reduced spacing before publisher for tighter cover layout
                                elements.append(Spacer(1, 0.5 * 72))
                                elements.append(
                                    self._create_paragraph(text, styles["front-cover-publisher"])
                                )

            except Exception as e:
                logger.error(f"PDFGenerator: Failed to process front cover image: {e}")
                elements.append(Spacer(1, 3 * 72))
                elements.append(
                    self._create_paragraph("Cover Image Not Available", styles["front-cover-title"])
                )
        else:
            logger.warning(f"PDFGenerator: Front cover image not found: {front_cover_path}")
            elements.append(Spacer(1, 3 * 72))
            elements.append(self._create_paragraph("Front Cover", styles["front-cover-title"]))

        # Switch back to normal template for content pages
        elements.append(NextPageTemplate("normal"))
        elements.append(PageBreak())  # New page after front cover
        return elements

    def _process_back_cover_page(self, div_element, styles) -> list:
        """Process back cover page with background image and text overlay."""
        from fable_flow.config import config

        elements = []

        # Switch to cover page template (minimal margins, no page numbers)
        elements.append(NextPageTemplate("cover"))

        # Try to load the back cover image as background
        back_cover_path = self.output_dir / "back_cover.png"
        if back_cover_path.exists():
            try:
                # Use maximized dimensions for cover with minimal padding
                # This makes the cover fill most of the page like a real book
                img_width, img_height = self._calculate_cover_image_size(
                    back_cover_path, self._cover_max_width, self._cover_max_height
                )

                background_image = RLImage(str(back_cover_path), width=img_width, height=img_height)
                elements.append(background_image)

                # Use negative spacer based on actual image height to overlay text
                # Minimal offset to ensure all content fits on one page
                elements.append(Spacer(1, -img_height + (1 * 72)))

                overlay_div = div_element.find("div", class_="back-cover-text-overlay")
                if overlay_div:
                    content_div = overlay_div.find("div", class_="back-cover-content")
                    if content_div:
                        # Minimal top spacing to ensure content fits
                        elements.append(Spacer(1, 1 * 72))
                        description_div = content_div.find("div", class_="back-cover-description")
                        if description_div:
                            text = description_div.get_text().strip()
                            if text:
                                elements.append(
                                    self._create_paragraph(text, styles["back-cover-description"])
                                )

                    footer_div = overlay_div.find("div", class_="back-cover-footer")
                    if footer_div:
                        # Minimal spacing to ensure ISBN and logo fit on same page
                        elements.append(Spacer(1, 1.5 * 72))

                        publisher_div = footer_div.find("div", class_="publisher-info")
                        if publisher_div:
                            for child in publisher_div.children:
                                if isinstance(child, NavigableString):
                                    continue
                                if hasattr(child, "name"):
                                    text = child.get_text().strip()
                                    if text:
                                        if "back-cover-publisher" in child.get("class", []):
                                            elements.append(
                                                self._create_paragraph(
                                                    text, styles["back-cover-publisher"]
                                                )
                                            )
                                        elif "back-cover-location" in child.get("class", []):
                                            elements.append(
                                                self._create_paragraph(
                                                    text, styles["back-cover-location"]
                                                )
                                            )

                        isbn_logo_div = footer_div.find("div", class_="isbn-logo-section")
                        if isbn_logo_div:
                            isbn_p = isbn_logo_div.find("p", class_="isbn")
                            if isbn_p:
                                isbn_text = isbn_p.get_text().strip()
                                elements.append(self._create_paragraph(isbn_text, styles["isbn"]))

                            if _LOGO_PATH.exists():
                                try:
                                    logo_image = RLImage(
                                        str(_LOGO_PATH), width=2 * 72, height=0.5 * 72
                                    )
                                    elements.append(logo_image)
                                except Exception as e:
                                    logger.error(f"PDFGenerator: Failed to add logo: {e}")

            except Exception as e:
                logger.error(f"PDFGenerator: Failed to process back cover image: {e}")
                elements.append(Spacer(1, 8 * 72))
                elements.append(
                    self._create_paragraph("Back Cover", styles["back-cover-description"])
                )
        else:
            logger.warning(f"PDFGenerator: Back cover image not found: {back_cover_path}")
            elements.append(Spacer(1, 8 * 72))
            elements.append(self._create_paragraph("Back Cover", styles["back-cover-description"]))

        # No page break after back cover (it's the last page)
        return elements

    def _process_explicit_title_page(self, div_element, styles) -> list:
        """Process explicit title page with programmatically generated content and logo.

        Regenerates the title page HTML using BookStructureGenerator to ensure
        correct author attribution and consistent metadata.
        """

        elements = []
        elements.append(Spacer(1, 1.5 * 72))  # Reduced top spacing to fit on one page

        # Regenerate title page HTML with correct metadata (like EPUB does)
        logger.info("PDFGenerator: Regenerating title page HTML with BookStructureGenerator")
        structure_gen = BookStructureGenerator(self.output_dir, self._book_metadata, format="pdf")
        fresh_html = structure_gen.generate_title_page_html()

        # Parse the regenerated HTML
        fresh_soup = BeautifulSoup(fresh_html, "html.parser")
        title_page = fresh_soup.find("div", class_="explicit-title-page")

        # Find the content div from regenerated HTML
        content_div = title_page.find("div", class_="title-page-content") if title_page else None
        if content_div:
            for child in content_div.children:
                if isinstance(child, NavigableString):
                    continue

                if hasattr(child, "name"):
                    # Handle "Powered by" section with logo
                    if child.name == "div" and "powered-by-section" in child.get("class", []):
                        elements.append(Spacer(1, 1 * 72))  # Reduced spacing

                        # Add "Powered by" text
                        powered_by_text = child.find("p", class_="powered-by-text")
                        if powered_by_text:
                            text = powered_by_text.get_text().strip()
                            elements.append(self._create_paragraph(text, styles["powered-by-text"]))

                        # Add FableFlow logo
                        logo_img = child.find("img", class_="fableflow-logo")
                        if logo_img and _LOGO_PATH.exists():
                            try:
                                logo = RLImage(str(_LOGO_PATH), width=3 * 72, height=0.75 * 72)
                                elements.append(logo)
                                logger.info("PDFGenerator: Added FableFlow logo to title page")
                            except Exception as e:
                                logger.error(f"PDFGenerator: Failed to add logo: {e}")

                        elements.append(Spacer(1, 1 * 72))  # Reduced spacing
                        continue

                    text = child.get_text().strip()
                    if not text:
                        continue

                    if child.name == "h1" and "title-page-title" in child.get("class", []):
                        elements.append(self._create_paragraph(text, styles["title-page-title"]))
                        elements.append(Spacer(1, 0.3 * 72))  # Minimal spacing
                        logger.info(f"PDFGenerator: Title page title: {text}")
                    elif child.name == "h2" and "title-page-subtitle" in child.get("class", []):
                        elements.append(self._create_paragraph(text, styles["title-page-subtitle"]))
                        elements.append(Spacer(1, 0.5 * 72))  # Reduced spacing
                        logger.info(f"PDFGenerator: Title page subtitle: {text}")
                    elif child.name == "p" and "title-page-author" in child.get("class", []):
                        elements.append(Spacer(1, 0.5 * 72))  # Reduced spacing
                        elements.append(self._create_paragraph(text, styles["title-page-author"]))
                        logger.info(f"PDFGenerator: Title page author: {text}")
                    elif child.name == "p" and "title-page-publisher" in child.get("class", []):
                        elements.append(Spacer(1, 1 * 72))  # Reduced spacing
                        elements.append(
                            self._create_paragraph(text, styles["title-page-publisher"])
                        )

        elements.append(PageBreak())  # New page after title page
        # Add invisible content to force blank page to exist
        elements.append(Paragraph("&nbsp;", styles.get("Normal", styles.get("body-text"))))
        elements.append(PageBreak())  # Move past the blank page
        return elements

    def _process_publication_info(self, div_element, styles) -> list:
        """Process publication information page with improved styling."""
        elements = []
        elements.append(Spacer(1, 3 * 72))  # Top spacing

        # Process all paragraphs in publication info with specific styles
        for child in div_element.children:
            if isinstance(child, NavigableString):
                continue

            if hasattr(child, "name"):
                # Handle spacer divs
                if child.name == "div" and "pub-spacing" in child.get("class", []):
                    elements.append(Spacer(1, 0.5 * 72))
                    continue

                if child.name == "p":
                    text = child.get_text().strip()
                    if not text:
                        continue

                    # Determine style based on class
                    classes = child.get("class", [])
                    if "pub-publisher" in classes:
                        elements.append(self._create_paragraph(text, styles["pub-publisher"]))
                    elif "pub-edition" in classes:
                        elements.append(self._create_paragraph(text, styles["pub-edition"]))
                    elif "pub-credits" in classes:
                        elements.append(self._create_paragraph(text, styles["pub-credits"]))
                    elif "pub-copyright" in classes:
                        elements.append(self._create_paragraph(text, styles["pub-copyright"]))
                    elif "pub-isbn" in classes or "ISBN" in text:
                        elements.append(self._create_paragraph(text, styles["pub-isbn"]))
                    elif "pub-disclaimer" in classes:
                        elements.append(self._create_paragraph(text, styles["pub-disclaimer"]))
                    else:
                        elements.append(self._create_paragraph(text, styles["publication-info"]))

                    elements.append(Spacer(1, 6))  # Small space between items
                elif child.name == "br":
                    elements.append(Spacer(1, 12))  # Line break spacing

        elements.append(PageBreak())  # New page after publication info
        return elements

    def _process_table_of_contents(self, div_element, styles) -> list:
        """Process table of contents with clickable links and accurate page numbers."""
        elements = []

        for child in div_element.children:
            if isinstance(child, NavigableString):
                continue

            if hasattr(child, "name"):
                if child.name == "h2" and "toc-title" in child.get("class", []):
                    text = child.get_text().strip()
                    elements.append(self._create_paragraph(text, styles["toc-title"]))
                elif "toc-entry" in child.get("class", []):
                    # Extract chapter name (ignore old page reference)
                    chapter_name_span = child.find("span", class_="chapter-name")

                    if chapter_name_span:
                        entry_name = chapter_name_span.get_text().strip()

                        # Look for bookmark in both chapters and sections
                        bookmark_name = self._chapter_bookmarks.get(
                            entry_name
                        ) or self._section_bookmarks.get(entry_name)

                        if bookmark_name:
                            # Get actual page number from tracking
                            page_num = self._bookmark_pages.get(bookmark_name, "?")

                            # Create clickable link with actual page number
                            toc_text = f'<a href="#{bookmark_name}" color="blue">{entry_name}</a>'
                            if page_num != "?":
                                # Add page number with leader dots
                                toc_text += f' <font color="#666666">{"." * 20}</font> {page_num}'

                            logger.info(
                                f"PDFGenerator: Created TOC entry '{entry_name}' -> page {page_num}"
                            )
                        else:
                            # Fallback: no bookmark found
                            toc_text = entry_name
                            logger.warning(f"PDFGenerator: No bookmark found for '{entry_name}'")

                        elements.append(self._create_paragraph(toc_text, styles["toc-entry"]))
                    else:
                        # Fallback for non-standard TOC entry format
                        text = child.get_text().strip()
                        elements.append(self._create_paragraph(text, styles["toc-entry"]))
                elif child.name in ["p", "div"]:
                    text = child.get_text().strip()
                    if text:
                        elements.append(self._create_paragraph(text, styles["toc-entry"]))

        # Add entries for sections not in the generated TOC (preface, about, acknowledgments, index)
        # These are typically generated after the TOC but should be listed
        for section_title, bookmark_name in self._section_bookmarks.items():
            page_num = self._bookmark_pages.get(bookmark_name, "?")
            toc_text = f'<a href="#{bookmark_name}" color="blue">{section_title}</a>'
            if page_num != "?":
                toc_text += f' <font color="#666666">{"." * 20}</font> {page_num}'
            elements.append(self._create_paragraph(toc_text, styles["toc-entry"]))
            logger.info(f"PDFGenerator: Added section to TOC: '{section_title}' -> page {page_num}")

        elements.append(PageBreak())  # New page after TOC
        elements.append(PageBreak())  # Explicit blank page
        return elements

    def _process_preface(self, div_element, styles) -> list:
        """Process preface/foreword elements."""
        elements = []
        bookmark_added = False

        for child in div_element.children:
            if isinstance(child, NavigableString):
                continue

            if hasattr(child, "name"):
                text = child.get_text().strip()
                if not text:
                    continue

                if child.name in ["h1", "h2"]:
                    # Add bookmark for the first heading
                    if not bookmark_added:
                        bookmark_name = self._section_bookmarks.get(text)
                        if bookmark_name:
                            elements.append(
                                BookmarkFlowable(bookmark_name, text, self._bookmark_pages)
                            )
                            bookmark_added = True
                    elements.append(self._create_paragraph(text, styles["preface-title"]))
                else:
                    elements.append(self._create_paragraph(text, styles["preface-text"]))

        return elements

    def _process_back_matter(self, div_element, styles, classes) -> list:
        """Process back matter elements (about author, acknowledgments, index)."""
        elements = []
        bookmark_added = False

        # Determine the appropriate title style
        title_style = styles["preface-title"]
        if "index" in classes:
            title_style = styles["index-title"]

        for child in div_element.children:
            if isinstance(child, NavigableString):
                continue

            if hasattr(child, "name"):
                text = child.get_text().strip()
                if not text:
                    continue

                if child.name in ["h1", "h2"]:
                    # Add bookmark for the first heading
                    if not bookmark_added:
                        bookmark_name = self._section_bookmarks.get(text)
                        if bookmark_name:
                            elements.append(
                                BookmarkFlowable(bookmark_name, text, self._bookmark_pages)
                            )
                            bookmark_added = True
                    elements.append(self._create_paragraph(text, title_style))
                elif "index-entry" in child.get("class", []):
                    elements.append(self._create_paragraph(text, styles["index-entry"]))
                else:
                    elements.append(self._create_paragraph(text, styles["preface-text"]))

        return elements

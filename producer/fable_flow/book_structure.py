"""Unified generator for book structural elements (covers, title pages, publication info).

This module provides a clean, consistent way to generate the structural pages
of a children's book (covers, title page, publication info) that work identically
in both PDF and EPUB formats.
"""

from pathlib import Path
from typing import Optional

from loguru import logger

from fable_flow.config import config


class BookStructureGenerator:
    """Generate consistent book structural elements for PDF and EPUB."""

    def __init__(self, output_dir: Path, book_metadata: dict, format: str = "pdf"):
        """Initialize with output directory and book metadata.

        Args:
            output_dir: Directory containing book assets (images, etc.)
            book_metadata: Dictionary containing title, subtitle, author, etc.
            format: Output format - either 'pdf' or 'epub' (determines which ISBN to use)
        """
        self.output_dir = output_dir
        self.metadata = book_metadata
        self.format = format.lower()
        self.logo_path = (
            Path(__file__).parent.parent.parent / "docs" / "assets" / "logo_horizontal.png"
        )

        # Clean subtitle to avoid displaying "None"
        self._clean_metadata()

    def _clean_metadata(self) -> None:
        """Clean metadata to ensure no 'None' strings are displayed."""
        if self.metadata.get("subtitle") in [None, "None", "none", ""]:
            self.metadata["subtitle"] = ""

    def _get_subtitle_html(self, css_class: str) -> str:
        """Get subtitle HTML only if subtitle exists and is not empty.

        Args:
            css_class: CSS class name for the subtitle element

        Returns:
            HTML string for subtitle or empty string
        """
        subtitle = self.metadata.get("subtitle", "")
        if subtitle and subtitle.strip():
            return f'<h2 class="{css_class}">{subtitle}</h2>'
        return ""

    def generate_front_cover_html(self) -> str:
        """Generate front cover HTML with background image and text overlay.

        Returns:
            Complete HTML for front cover page-spread
        """
        title = self.metadata.get("title", "Untitled Story")
        # ALWAYS use config.book.draft_story_author for author attribution
        author = config.book.draft_story_author
        publisher = self.metadata.get("publisher", config.book.publisher)

        subtitle_html = self._get_subtitle_html("front-cover-subtitle")

        logger.info(f"BookStructure: Generating front cover for '{title}' by {author}")

        return f"""<div class="page-spread">
    <div class="page">
        <div class="front-cover-page">
            <div class="cover-background">
                <img src="front_cover.png" alt="Book Cover" class="cover-background-image"/>
            </div>
            <div class="cover-text-overlay">
                <h1 class="front-cover-title">{title}</h1>
                {subtitle_html}
                <p class="front-cover-author">By {author}</p>
                <p class="front-cover-publisher">{publisher}</p>
            </div>
        </div>
    </div>
</div>

"""

    def generate_title_page_html(self) -> str:
        """Generate explicit title page WITH FableFlow logo.

        This is the formal title page inside the book, featuring the title,
        subtitle, author, and prominent FableFlow branding.

        Returns:
            Complete HTML for title page-spread
        """
        title = self.metadata.get("title", "Untitled Story")
        # ALWAYS use config.book.draft_story_author for author attribution
        author = config.book.draft_story_author
        publisher = self.metadata.get("publisher", config.book.publisher)

        subtitle_html = self._get_subtitle_html("title-page-subtitle")

        logger.info(f"BookStructure: Generating title page with FableFlow logo for {author}")

        return f"""<div class="page-spread">
    <div class="page">
        <div class="explicit-title-page">
            <div class="title-page-content">
                <h1 class="title-page-title">{title}</h1>
                {subtitle_html}
                <p class="title-page-author">By {author}</p>

                <!-- POWERED BY FABLEFLOW LOGO -->
                <div class="powered-by-section">
                    <p class="powered-by-text">Powered by</p>
                    <img src="../../docs/assets/logo_horizontal.png"
                         alt="FableFlow"
                         class="fableflow-logo"/>
                </div>

                <p class="title-page-publisher">{publisher}</p>
            </div>
        </div>
    </div>
</div>

"""

    def generate_publication_info_html(self) -> str:
        """Generate publication information page.

        Creates a professional publication info page with copyright,
        ISBN, edition information, etc.

        Returns:
            Complete HTML for publication info page-spread
        """
        publisher = self.metadata.get("publisher", config.book.publisher)
        edition = getattr(config.book, "edition", "First Edition")
        year = getattr(config.book, "publication_year", "2024")
        author = config.book.draft_story_author
        # Use appropriate ISBN based on output format
        isbn = config.book.isbn_epub if self.format == "epub" else config.book.isbn_pdf

        logger.info("BookStructure: Generating publication info page")

        return f"""<div class="page-spread">
    <div class="page">
        <div class="publication-info">
            <p class="pub-publisher"><strong>{publisher}</strong></p>
            <p class="pub-edition">{edition}, {year}</p>

            <div class="pub-spacing"></div>

            <p class="pub-credits">
                Based on original story by {author}<br/>
                Enhanced with AI by FableFlow
            </p>

            <div class="pub-spacing"></div>

            <p class="pub-copyright">All rights reserved</p>

            <div class="pub-spacing"></div>

            <p class="pub-isbn"><strong>ISBN: {isbn}</strong></p>

            <div class="pub-spacing"></div>

            <p class="pub-disclaimer">
                No part of this publication may be reproduced, stored in a retrieval system,<br/>
                or transmitted in any form or by any means without prior written permission.
            </p>
        </div>
    </div>
</div>

"""

    def generate_back_cover_html(self) -> str:
        """Generate back cover HTML with background image and text overlay.

        Returns:
            Complete HTML for back cover page-spread
        """
        # title = self.metadata.get("title", "Untitled Story")
        publisher = self.metadata.get("publisher", config.book.publisher)
        publisher_location = getattr(config.book, "publisher_location", "")
        # Use appropriate ISBN based on output format
        isbn = config.book.isbn_epub if self.format == "epub" else config.book.isbn_pdf

        description = self.metadata.get(
            "description",
            "An engaging educational children's book that combines storytelling with learning, "
            "designed to inspire curiosity and wonder in young readers.",
        )

        logger.info("BookStructure: Generating back cover")

        return f"""<div class="page-spread">
    <div class="page">
        <div class="back-cover-page">
            <div class="cover-background">
                <img src="back_cover.png" alt="Back Cover" class="cover-background-image"/>
            </div>
            <div class="back-cover-text-overlay">
                <div class="back-cover-content">
                    <div class="back-cover-description">
                        <p>{description}</p>
                    </div>
                </div>
                <div class="back-cover-footer">
                    <div class="publisher-info">
                        <p class="back-cover-publisher">{publisher}</p>
                        <p class="back-cover-location">{publisher_location}</p>
                    </div>
                    <div class="isbn-logo-section">
                        <p class="isbn">ISBN {isbn}</p>
                        <img src="../../docs/assets/logo_horizontal.svg" alt="FableFlow Logo" class="back-cover-logo"/>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

"""

    def generate_all_front_matter(self) -> str:
        """Generate all front matter pages in correct order.

        Returns:
            Combined HTML for front cover, title page, and publication info
        """
        return (
            self.generate_front_cover_html()
            + self.generate_title_page_html()
            + self.generate_publication_info_html()
        )

    def generate_complete_book_structure(self, story_content: str) -> str:
        """Generate complete book with front matter, content, and back matter.

        Args:
            story_content: The main story content HTML (chapters, etc.)

        Returns:
            Complete book HTML from cover to cover
        """
        logger.info("BookStructure: Assembling complete book structure")

        return (
            self.generate_front_cover_html()
            + self.generate_title_page_html()
            + self.generate_publication_info_html()
            + story_content
            + self.generate_back_cover_html()
        )

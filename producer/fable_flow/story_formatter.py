"""Deterministic HTML formatter for story content that preserves exact wording.

This module provides a programmatic approach to wrapping story text in HTML markup
WITHOUT using an LLM, ensuring that the original story wording is preserved exactly.
"""

import re

from loguru import logger


class StoryHTMLFormatter:
    """Formats story content into HTML with exact text preservation."""

    def __init__(self, story_text: str, image_positions: dict[str, str] = None):
        """Initialize formatter with story text and optional image positions.

        Args:
            story_text: The exact story text to format (from final_story.txt)
            image_positions: Optional dict mapping image markup to descriptions
        """
        self.story_text = story_text
        self.image_positions = image_positions or {}

    @staticmethod
    def detect_chapters(story_text: str) -> list[tuple[str, str]]:
        """Detect chapters in the story text.

        Looks for patterns like:
        - "Chapter 1: Title" or "Chapter One: Title"
        - "## Chapter 1:" (markdown H2 with "Chapter")
        - "# " at start (markdown H1 - typically book title, skip in chapter content)

        Args:
            story_text: The story text to analyze

        Returns:
            List of tuples (chapter_title, chapter_content)
        """
        chapters = []

        # Patterns to detect chapter headers
        # 1. "Chapter N:" with optional title
        chapter_pattern = r"^(?:##\s*)?Chapter\s+(?:\d+|One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten)(?:[:\s].*)?$"

        lines = story_text.split("\n")
        current_chapter_title = None
        current_chapter_content = []
        book_title_seen = False

        for _i, line in enumerate(lines):
            stripped = line.strip()

            # Skip book title (first # heading) and subtitle (first ##)
            if not book_title_seen and stripped.startswith("#"):
                book_title_seen = True
                continue

            # Check for chapter headers (with or without ## markdown)
            if re.match(chapter_pattern, stripped, re.IGNORECASE):
                # Save previous chapter if exists
                if current_chapter_title is not None:
                    chapters.append((current_chapter_title, "\n".join(current_chapter_content)))

                # Start new chapter - clean up the title
                current_chapter_title = stripped.lstrip("#").strip()
                current_chapter_content = []
                logger.debug(f"StoryFormatter: Found chapter: {current_chapter_title}")

            # Content line
            elif current_chapter_title is not None:
                # Skip empty lines at the start of a chapter
                if not current_chapter_content and not stripped:
                    continue
                current_chapter_content.append(line)
            else:
                # Content before first chapter (skip book metadata at start)
                if stripped and not stripped.startswith("#") and not stripped.startswith("---"):
                    current_chapter_content.append(line)

        # Add final chapter
        if current_chapter_title is not None:
            chapters.append((current_chapter_title, "\n".join(current_chapter_content)))
        elif current_chapter_content:
            # No chapters detected, treat entire story as single chapter
            chapters.append(("Story", "\n".join(current_chapter_content)))

        logger.info(f"StoryFormatter: Detected {len(chapters)} chapter(s)")
        return chapters

    @staticmethod
    def detect_poems(text: str) -> str:
        """Detect and wrap poem sections in HTML.

        Looks for lines marked with asterisks (e.g., *Can't builds a wall*)
        and wraps them in poem HTML structure.

        Args:
            text: Text that may contain poem markers

        Returns:
            Text with poems wrapped in HTML
        """
        # Pattern: lines starting with * and ending with * (poem markers)
        poem_line_pattern = r"^\s*\*(.+?)\*\s*$"

        lines = text.split("\n")
        result_lines = []
        in_poem = False
        poem_lines = []

        for line in lines:
            if re.match(poem_line_pattern, line):
                # This is a poem line
                match = re.match(poem_line_pattern, line)
                poem_text = match.group(1).strip()

                if not in_poem:
                    # Start of poem
                    in_poem = True
                    poem_lines = [poem_text]
                else:
                    # Continue poem
                    poem_lines.append(poem_text)
            else:
                # Not a poem line
                if in_poem:
                    # End of poem - wrap it
                    poem_html = '<div class="poem-box"><p class="poem-verse">'
                    poem_html += "<br/>".join(poem_lines)
                    poem_html += "</p></div>"
                    result_lines.append(poem_html)

                    in_poem = False
                    poem_lines = []

                # Add the non-poem line
                result_lines.append(line)

        # Handle poem at end of text
        if in_poem and poem_lines:
            poem_html = '<div class="poem-box"><p class="poem-verse">'
            poem_html += "<br/>".join(poem_lines)
            poem_html += "</p></div>"
            result_lines.append(poem_html)

        return "\n".join(result_lines)

    @staticmethod
    def wrap_paragraphs(text: str) -> str:
        """Wrap text paragraphs in HTML <p> tags.

        Preserves existing HTML tags (like poem-box, image divs) and only wraps plain text.

        Args:
            text: Text with line breaks separating paragraphs

        Returns:
            Text with paragraphs wrapped in <p class="story-text"> tags
        """
        lines = text.split("\n")
        result_lines = []
        current_paragraph = []

        for line in lines:
            stripped = line.strip()

            # Check if this line contains HTML tags or image placeholders (don't wrap it)
            if (
                "<div" in line
                or "</div>" in line
                or "<p" in line
                or "</p>" in line
                or "IMAGE_PLACEHOLDER" in line
                or "<img" in line
            ):
                # Finish current paragraph if any
                if current_paragraph:
                    para_text = " ".join(current_paragraph)
                    if para_text:
                        result_lines.append(f'<p class="story-text">{para_text}</p>')
                    current_paragraph = []

                # Add the HTML line as-is
                result_lines.append(line)

            # Empty line signals paragraph break
            elif not stripped:
                if current_paragraph:
                    para_text = " ".join(current_paragraph)
                    if para_text:
                        result_lines.append(f'<p class="story-text">{para_text}</p>')
                    current_paragraph = []

            # Regular text line
            else:
                current_paragraph.append(stripped)

        # Add final paragraph if exists
        if current_paragraph:
            para_text = " ".join(current_paragraph)
            if para_text:
                result_lines.append(f'<p class="story-text">{para_text}</p>')

        result = "\n".join(result_lines)

        # Remove placeholder markers
        result = result.replace("IMAGE_PLACEHOLDER_START\n", "").replace(
            "\nIMAGE_PLACEHOLDER_END", ""
        )

        return result

    def process_image_markup(self, text: str) -> str:
        """Process image markup tags and convert to proper HTML.

        Converts <image>1 [description]</image> to proper HTML img tags.
        NOTE: Markup uses 1-based numbering but files are 0-based (image_0.png).

        Args:
            text: Text containing <image>...</image> markup

        Returns:
            Text with images converted to HTML img tags
        """
        # Pattern: <image>NUMBER [description]</image>
        image_pattern = r"<image>\s*(\d+)\s*\[([^\]]+)\]</image>"

        def replace_image(match):
            markup_number = int(match.group(1))
            description = match.group(2).strip()

            # Convert 1-based markup to 0-based filename
            file_number = markup_number - 1

            # Determine image placement class based on position in text
            # For now, use full-page as default
            image_class = "image-full-page"

            # Use special marker that won't be wrapped in paragraph tags
            html = f'''IMAGE_PLACEHOLDER_START
<div class="{image_class}">
    <img src="image_{file_number}.png" alt="{description}">
    <div class="caption">{description}</div>
</div>
IMAGE_PLACEHOLDER_END'''

            logger.debug(
                f"StoryFormatter: Converting image markup {markup_number} -> image_{file_number}.png"
            )
            return html

        result = re.sub(image_pattern, replace_image, text, flags=re.DOTALL)
        return result

    def format_chapter_html(self, chapter_title: str, chapter_content: str) -> str:
        """Format a single chapter with HTML markup.

        Args:
            chapter_title: The chapter title
            chapter_content: The chapter content (plain text)

        Returns:
            Complete HTML for the chapter in page-spread format
        """
        # Process in order:
        # 1. Convert image markup to HTML
        content = self.process_image_markup(chapter_content)

        # 2. Detect and wrap poems
        content = self.detect_poems(content)

        # 3. Wrap paragraphs
        content = self.wrap_paragraphs(content)

        # 4. Wrap in chapter structure
        chapter_html = f"""<div class="page-spread">
    <div class="page">
        <h2 class="chapter-title">{chapter_title}</h2>
        {content}
    </div>
</div>

"""
        return chapter_html

    def format_story_to_html(self) -> str:
        """Convert story text to complete HTML while preserving exact wording.

        Returns:
            HTML string with story content wrapped in proper markup
        """
        logger.info("StoryFormatter: Starting deterministic HTML formatting")

        # Detect chapters
        chapters = self.detect_chapters(self.story_text)

        if not chapters:
            logger.warning("StoryFormatter: No chapters detected, treating as single story")
            chapters = [("Story", self.story_text)]

        # Format each chapter
        html_parts = []
        for chapter_title, chapter_content in chapters:
            chapter_html = self.format_chapter_html(chapter_title, chapter_content)
            html_parts.append(chapter_html)

        # Combine all chapters
        complete_html = "".join(html_parts)

        logger.info(f"StoryFormatter: Generated {len(html_parts)} chapter(s) HTML")
        return complete_html

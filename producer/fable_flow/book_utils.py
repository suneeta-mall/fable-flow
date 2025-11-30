"""Shared utilities for book content processing.

This module provides common functions used by both PDF and EPUB generators
to avoid code duplication and ensure consistency.
"""

import re
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup
from loguru import logger

_LOGO_PATH = Path(__file__).parent.parent.parent / "docs" / "assets" / "logo_horizontal.png"


class BookContentProcessor:
    """Shared utilities for processing book content across PDF and EPUB."""

    @staticmethod
    def clean_html_content(html_content: str) -> str:
        """Remove markdown code blocks and clean HTML formatting.

        Args:
            html_content: Raw HTML content, possibly with markdown markers

        Returns:
            Cleaned HTML content
        """
        # Remove markdown code block markers
        html_content = re.sub(r"^```html\s*\n?", "", html_content, flags=re.MULTILINE)
        html_content = re.sub(r"\n?```\s*$", "", html_content, flags=re.MULTILINE)
        html_content = re.sub(r"^```\s*\n?", "", html_content, flags=re.MULTILINE)

        # Remove any stray backticks
        html_content = html_content.strip("`")

        # Clean up extra whitespace
        html_content = html_content.strip()

        logger.debug("BookContentProcessor: Cleaned HTML content")
        return html_content

    @staticmethod
    def fix_subtitle_display(metadata: dict) -> dict:
        """Ensure subtitle is empty string, not 'None'.

        Args:
            metadata: Book metadata dictionary

        Returns:
            Cleaned metadata dictionary
        """
        if metadata.get("subtitle") in [None, "None", "none", ""]:
            metadata["subtitle"] = ""
        return metadata

    @staticmethod
    def collect_images(
        output_dir: Path, include_covers: bool = True, include_logos: bool = True
    ) -> list[Path]:
        """Collect all image files that should be included in the book.

        Args:
            output_dir: Directory containing image files
            include_covers: Whether to include front/back cover images
            include_logos: Whether to include logo files

        Returns:
            List of Path objects for all images to include
        """
        image_extensions = {".png", ".jpg", ".jpeg", ".gif", ".svg"}
        images = []

        for image_file in output_dir.iterdir():
            if not image_file.is_file():
                continue

            if image_file.suffix.lower() not in image_extensions:
                continue

            # Filter based on filename
            is_cover = "cover" in image_file.stem.lower()
            is_logo = "logo" in image_file.stem.lower()

            if not include_covers and is_cover:
                continue

            if not include_logos and is_logo:
                continue

            images.append(image_file)

        # Ensure cover images are included if requested
        if include_covers:
            front_cover = output_dir / "front_cover.png"
            back_cover = output_dir / "back_cover.png"
            if front_cover.exists() and front_cover not in images:
                images.append(front_cover)
            if back_cover.exists() and back_cover not in images:
                images.append(back_cover)

        # Ensure logo is included if requested
        if include_logos:
            if _LOGO_PATH.exists() and _LOGO_PATH not in images:
                images.append(_LOGO_PATH)

        logger.info(f"BookContentProcessor: Collected {len(images)} images")
        return sorted(images)

    @staticmethod
    def extract_image_references(html_content: str) -> dict[int, str]:
        """Extract all image references from HTML content.

        Supports both <img src="..."> and legacy <image>...</image> formats.

        Args:
            html_content: HTML content to extract from

        Returns:
            Dictionary mapping image index to image reference
        """
        # Pattern for standard <img src="..."> tags
        img_pattern = r'<img[^>]*src="([^"]+)"[^>]*>'
        img_matches = re.findall(img_pattern, html_content, re.DOTALL)

        # Pattern for legacy <image>...</image> tags
        image_pattern = r"<image[^>]*>(.*?)</image>"
        image_matches = re.findall(image_pattern, html_content, re.DOTALL)

        image_map = {}
        current_index = 0

        # Process <img> tags first, but exclude cover images
        for match in img_matches:
            image_ref = match.strip()
            # Skip cover images - only include content images (image_X.png pattern)
            if image_ref and (image_ref.startswith("image_") and image_ref.endswith(".png")):
                image_map[current_index] = image_ref
                logger.debug(f"BookContentProcessor: Found img src {current_index}: '{image_ref}'")
                current_index += 1

        # Then process legacy <image> tags
        for match in image_matches:
            image_ref = match.strip()
            if image_ref:
                image_map[current_index] = image_ref
                logger.debug(
                    f"BookContentProcessor: Found image tag {current_index}: '{image_ref}'"
                )
                current_index += 1

        logger.info(f"BookContentProcessor: Extracted {len(image_map)} image references")
        return image_map

    @staticmethod
    def parse_html_structure(html_content: str) -> tuple[BeautifulSoup, Any | None]:
        """Parse HTML and find the main book div.

        Args:
            html_content: HTML content to parse

        Returns:
            Tuple of (BeautifulSoup object, book div element or None)
        """
        soup = BeautifulSoup(html_content, "html.parser")
        book_div = soup.find("div", class_="book")

        if not book_div:
            logger.warning("BookContentProcessor: No book div found in HTML")

        return soup, book_div

    @staticmethod
    def is_descendant_of(child, parent) -> bool:
        """Check if child element is a descendant of parent element.

        Args:
            child: BeautifulSoup element to check
            parent: Potential parent element

        Returns:
            True if child is descendant of parent
        """
        if not child or not parent:
            return False

        current = child.parent
        while current:
            if current == parent:
                return True
            current = current.parent

        return False

    @staticmethod
    def fix_image_paths_for_epub(content_html: str) -> str:
        """Fix image paths to point to EPUB images directory.

        Also fixes malformed img tags with broken alt attributes for EPUB XML validation.

        Args:
            content_html: HTML content with image tags

        Returns:
            HTML with corrected image paths and sanitized img tags
        """
        # FIRST: Fix malformed img tags with multiple ="" attributes
        # Pattern: <img ... alt="text" word1="" word2="" ... src="...">
        # This is specific to EPUB XHTML strict validation requirements

        def fix_malformed_alt(match):
            """Fix img tags where alt text has unescaped quotes creating ="" fragments."""
            img_tag = match.group(0)

            # Extract the essential attributes
            src_match = re.search(r'src=["\']([^"\']+)["\']', img_tag)
            alt_match = re.search(r'alt="([^"]*)"', img_tag)
            class_match = re.search(r'class=["\']([^"\']+)["\']', img_tag)

            if not src_match:
                return img_tag  # No src, leave as is

            src = src_match.group(1)
            alt_text = alt_match.group(1) if alt_match else ""
            class_attr = f' class="{class_match.group(1)}"' if class_match else ""

            # Collect all word="" fragments after alt and before src
            if alt_match and "src=" in img_tag:
                alt_end = alt_match.end()
                src_start = img_tag.find("src=", alt_end)
                between_text = img_tag[alt_end:src_start]

                # Find all word="" patterns
                fragments = re.findall(r'(\S+)=""', between_text)
                if fragments:
                    # Add fragments to alt text
                    alt_text = alt_text + " " + " ".join(fragments)
                    # Replace quotes with single quotes for safety
                    alt_text = alt_text.replace('"', "'").replace("  ", " ").strip()
                    logger.debug(
                        f"BookContentProcessor: Fixed malformed img alt text ({len(fragments)} fragments)"
                    )

            return f'<img src="{src}"{class_attr} alt="{alt_text}"/>'

        # Look for img tags with multiple ="" (sign of malformed attributes)
        malformed_pattern = r'<img[^>]*=""[^>]*=""[^>]*>'
        content_html = re.sub(malformed_pattern, fix_malformed_alt, content_html, flags=re.DOTALL)

        # SECOND: Fix image paths to use EPUB images/ directory
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

    @staticmethod
    def validate_book_metadata(metadata: dict) -> dict:
        """Validate and ensure all required metadata fields exist.

        Args:
            metadata: Book metadata dictionary

        Returns:
            Validated metadata with defaults for missing fields
        """
        defaults = {
            "title": "Untitled Story",
            "subtitle": "",
            "author": "FableFlow",
            "publisher": "FableFlow Publishing",
            "description": "An engaging children's book.",
            "age_group": "Ages 5-10",
            "themes": "Adventure, Learning, Friendship",
        }

        # Fill in missing fields with defaults
        for key, default_value in defaults.items():
            if key not in metadata or not metadata[key]:
                metadata[key] = default_value
                logger.debug(f"BookContentProcessor: Using default for '{key}': {default_value}")

        # Clean subtitle
        metadata = BookContentProcessor.fix_subtitle_display(metadata)

        return metadata

    @staticmethod
    def extract_chapter_titles(soup: BeautifulSoup) -> list[str]:
        """Extract all chapter titles from parsed HTML.

        Args:
            soup: BeautifulSoup parsed HTML

        Returns:
            List of chapter title strings
        """
        chapters = []
        chapter_elements = soup.find_all("h2", class_="chapter-title")

        for element in chapter_elements:
            title = element.get_text().strip()
            if title:
                chapters.append(title)

        logger.info(f"BookContentProcessor: Found {len(chapters)} chapter titles")
        return chapters

    @staticmethod
    def verify_and_fix_author_attribution(html_content: str) -> str:
        """Verify and fix author attribution in HTML to use correct author name.

        This ensures that the author is always shown as the original author from config,
        not as 'FableFlow'. It replaces incorrect author attributions in cover and title pages.

        Args:
            html_content: Complete HTML content of the book

        Returns:
            HTML content with corrected author attribution
        """
        from fable_flow.config import config

        correct_author = config.book.draft_story_author
        logger.info(
            f"BookContentProcessor: Verifying author attribution (should be: {correct_author})"
        )

        # Count issues before fixing
        issues_found = 0

        # Pattern 1: Fix "By FableFlow" on covers and title pages
        if "By FableFlow</p>" in html_content:
            issues_found += html_content.count("By FableFlow</p>")
            html_content = html_content.replace("By FableFlow</p>", f"By {correct_author}</p>")
            logger.warning(
                f"BookContentProcessor: Fixed {issues_found} instances of 'By FableFlow' -> 'By {correct_author}'"
            )

        # Pattern 2: Fix front-cover-author class specifically
        pattern = rf'<p class="front-cover-author">By (?!{re.escape(correct_author)}).*?</p>'
        matches = re.findall(pattern, html_content)
        if matches:
            html_content = re.sub(
                pattern,
                f'<p class="front-cover-author">By {correct_author}</p>',
                html_content,
            )
            logger.warning(
                f"BookContentProcessor: Fixed front-cover-author attribution to {correct_author}"
            )

        # Pattern 3: Fix title-page-author class specifically
        pattern = rf'<p class="title-page-author">By (?!{re.escape(correct_author)}).*?</p>'
        matches = re.findall(pattern, html_content)
        if matches:
            html_content = re.sub(
                pattern,
                f'<p class="title-page-author">By {correct_author}</p>',
                html_content,
            )
            logger.warning(
                f"BookContentProcessor: Fixed title-page-author attribution to {correct_author}"
            )

        if issues_found == 0:
            logger.info(
                f"BookContentProcessor: Author attribution verified - all instances show {correct_author}"
            )
        else:
            logger.info(f"BookContentProcessor: Fixed {issues_found} author attribution issues")

        return html_content

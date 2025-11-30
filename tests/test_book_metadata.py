from pathlib import Path

import pytest

from fable_flow.book_structure import BookStructureGenerator
from fable_flow.book_utils import BookContentProcessor
from fable_flow.config import config


@pytest.fixture
def test_output_dir(tmp_path):
    """Provide a temporary output directory for tests."""
    return tmp_path / "test_output"


@pytest.fixture
def base_metadata():
    """Provide base metadata for book generation."""
    return {
        "title": "Test Book",
        "subtitle": "",
        "author": "Test Author",
        "publisher": "FableFlow Publishing",
    }


@pytest.fixture
def correct_author():
    """Provide the correct author from config."""
    return config.book.draft_story_author


@pytest.fixture
def structure_generator(test_output_dir, base_metadata):
    """Provide a BookStructureGenerator instance."""
    return BookStructureGenerator(test_output_dir, base_metadata)


class TestAuthorAttribution:
    def test_front_cover_uses_correct_author(self, test_output_dir, correct_author):
        """Front cover should use config.book.draft_story_author, not metadata author."""
        metadata = {
            "title": "Test Book",
            "subtitle": "A Test",
            "author": "FableFlow",  # Wrong author in metadata
            "publisher": "FableFlow Publishing",
        }

        structure_gen = BookStructureGenerator(test_output_dir, metadata)
        front_cover = structure_gen.generate_front_cover_html()

        assert f"By {correct_author}</p>" in front_cover, (
            f"Front cover should use correct author '{correct_author}', "
            f"not metadata author '{metadata['author']}'"
        )

    def test_title_page_uses_correct_author(self, test_output_dir, correct_author):
        """Title page should use config.book.draft_story_author, not metadata author."""
        metadata = {
            "title": "Test Book",
            "subtitle": "A Test",
            "author": "FableFlow",  # Wrong author in metadata
            "publisher": "FableFlow Publishing",
        }

        structure_gen = BookStructureGenerator(test_output_dir, metadata)
        title_page = structure_gen.generate_title_page_html()

        assert f"By {correct_author}</p>" in title_page, (
            f"Title page should use correct author '{correct_author}', "
            f"not metadata author '{metadata['author']}'"
        )

    def test_verification_function_fixes_wrong_author(self, correct_author):
        """Verification function should fix incorrect author attributions."""
        test_html = '<p class="front-cover-author">By FableFlow</p>'
        fixed_html = BookContentProcessor.verify_and_fix_author_attribution(test_html)

        assert f"By {correct_author}</p>" in fixed_html, (
            "Verification function should replace 'FableFlow' with correct author"
        )
        assert "By FableFlow</p>" not in fixed_html, (
            "Verification function should remove all instances of incorrect author"
        )

    def test_verification_preserves_correct_author(self, correct_author):
        """Verification function should not change correct author attributions."""
        test_html = f'<p class="front-cover-author">By {correct_author}</p>'
        fixed_html = BookContentProcessor.verify_and_fix_author_attribution(test_html)

        assert f"By {correct_author}</p>" in fixed_html, (
            "Verification function should preserve correct author"
        )

    @pytest.mark.parametrize(
        "class_name",
        ["front-cover-author", "title-page-author"],
    )
    def test_verification_fixes_all_author_classes(self, class_name, correct_author):
        """Verification function should fix author in all relevant CSS classes."""
        test_html = f'<p class="{class_name}">By WrongAuthor</p>'
        fixed_html = BookContentProcessor.verify_and_fix_author_attribution(test_html)

        assert f"By {correct_author}</p>" in fixed_html, f"Should fix author in {class_name} class"


class TestSubtitleHandling:
    @pytest.mark.parametrize(
        "subtitle,description",
        [
            (None, "None value"),
            ("None", "string 'None'"),
            ("", "empty string"),
            ("   ", "whitespace only"),
        ],
    )
    def test_empty_subtitle_is_hidden(self, test_output_dir, subtitle, description):
        """Empty or None subtitles should not appear in generated HTML."""
        metadata = {
            "title": "Test Book",
            "subtitle": subtitle,
            "author": "Test Author",
            "publisher": "Test Publisher",
        }

        structure_gen = BookStructureGenerator(test_output_dir, metadata)
        title_page = structure_gen.generate_title_page_html()

        assert "title-page-subtitle" not in title_page, (
            f"Subtitle should be hidden for {description}"
        )

    def test_real_subtitle_is_shown(self, test_output_dir):
        """Valid subtitles should appear in generated HTML."""
        metadata = {
            "title": "Test Book",
            "subtitle": "A Real Subtitle",
            "author": "Test Author",
            "publisher": "Test Publisher",
        }

        structure_gen = BookStructureGenerator(test_output_dir, metadata)
        title_page = structure_gen.generate_title_page_html()

        assert "title-page-subtitle" in title_page, "Valid subtitle should be included"
        assert "A Real Subtitle" in title_page, "Subtitle text should appear in HTML"

    def test_metadata_cleanup_removes_none_string(self, test_output_dir):
        """BookStructureGenerator should clean 'None' string in metadata."""
        metadata = {
            "title": "Test Book",
            "subtitle": "None",  # String 'None', not None value
            "author": "Test Author",
            "publisher": "Test Publisher",
        }

        structure_gen = BookStructureGenerator(test_output_dir, metadata)

        # After initialization, subtitle should be cleaned
        assert structure_gen.metadata["subtitle"] == "", (
            "BookStructureGenerator should clean 'None' string to empty string"
        )


class TestLogoPresence:
    def test_title_page_includes_powered_by_section(self, structure_generator):
        """Title page should include 'powered-by-section' div."""
        title_page = structure_generator.generate_title_page_html()

        assert "powered-by-section" in title_page, (
            "Title page should include powered-by-section div"
        )

    def test_title_page_references_logo_file(self, structure_generator):
        """Title page should reference logo_horizontal.png."""
        title_page = structure_generator.generate_title_page_html()

        assert "logo_horizontal.png" in title_page, (
            "Title page should reference FableFlow logo file"
        )

    def test_title_page_includes_powered_by_text(self, structure_generator):
        """Title page should include 'Powered by' text."""
        title_page = structure_generator.generate_title_page_html()

        assert "Powered by" in title_page, "Title page should include 'Powered by' text"

    def test_title_page_has_logo_css_class(self, structure_generator):
        """Title page logo should have correct CSS class."""
        title_page = structure_generator.generate_title_page_html()

        assert 'class="fableflow-logo"' in title_page, "Logo should have 'fableflow-logo' CSS class"


class TestPublicationInfo:
    @pytest.mark.parametrize(
        "css_class,description",
        [
            ("pub-publisher", "Publisher name"),
            ("pub-edition", "Edition info"),
            ("pub-credits", "Credits"),
            ("pub-isbn", "ISBN"),
            ("pub-disclaimer", "Copyright disclaimer"),
        ],
    )
    def test_publication_info_includes_required_elements(
        self, structure_generator, css_class, description
    ):
        """Publication info should include all required CSS classes and content."""
        pub_info = structure_generator.generate_publication_info_html()

        assert css_class in pub_info, f"Publication info should include {description}"

    def test_publication_info_credits_original_author(self, structure_generator, correct_author):
        """Publication info should credit the original story author."""
        pub_info = structure_generator.generate_publication_info_html()

        assert correct_author in pub_info, (
            f"Publication info should credit original author '{correct_author}'"
        )

    def test_publication_info_mentions_fableflow(self, structure_generator):
        """Publication info should mention FableFlow enhancement."""
        pub_info = structure_generator.generate_publication_info_html()

        assert "FableFlow" in pub_info, "Publication info should mention FableFlow enhancement"

    def test_publication_info_includes_isbn(self, structure_generator):
        """Publication info should include ISBN."""
        pub_info = structure_generator.generate_publication_info_html()

        isbn = config.book.isbn
        assert isbn in pub_info, f"Publication info should include ISBN: {isbn}"

    def test_publication_info_has_page_spread_structure(self, structure_generator):
        """Publication info should use proper page-spread structure."""
        pub_info = structure_generator.generate_publication_info_html()

        assert 'class="page-spread"' in pub_info, "Publication info should have page-spread wrapper"
        assert 'class="page"' in pub_info, "Publication info should have page div"
        assert 'class="publication-info"' in pub_info, (
            "Publication info should have publication-info div"
        )


class TestContentValidation:
    def test_validate_metadata_adds_defaults(self):
        """validate_book_metadata should add defaults for missing fields."""
        incomplete_metadata = {"title": "Test Book"}

        validated = BookContentProcessor.validate_book_metadata(incomplete_metadata)

        assert "subtitle" in validated, "Should add default subtitle"
        assert "author" in validated, "Should add default author"
        assert "publisher" in validated, "Should add default publisher"
        assert validated["subtitle"] == "", "Default subtitle should be empty"

    def test_validate_metadata_cleans_subtitle(self):
        """validate_book_metadata should clean 'None' subtitle."""
        metadata = {
            "title": "Test Book",
            "subtitle": "None",
            "author": "Test Author",
        }

        validated = BookContentProcessor.validate_book_metadata(metadata)

        assert validated["subtitle"] == "", "Metadata validation should clean 'None' subtitle"

    def test_validate_metadata_preserves_valid_values(self):
        """validate_book_metadata should not change valid metadata."""
        metadata = {
            "title": "Test Book",
            "subtitle": "A Real Subtitle",
            "author": "Test Author",
            "publisher": "Test Publisher",
        }

        validated = BookContentProcessor.validate_book_metadata(metadata)

        assert validated["title"] == metadata["title"], "Should preserve title"
        assert validated["subtitle"] == metadata["subtitle"], "Should preserve valid subtitle"
        assert validated["author"] == metadata["author"], "Should preserve author"


class TestBookStructureIntegration:
    def test_generate_all_front_matter(self, structure_generator, correct_author):
        """generate_all_front_matter should create consistent front matter."""
        front_matter = structure_generator.generate_all_front_matter()

        # Should include all three pages
        assert 'class="front-cover-page"' in front_matter, "Should include front cover"
        assert 'class="explicit-title-page"' in front_matter, "Should include title page"
        assert 'class="publication-info"' in front_matter, "Should include publication info"

        # Should use correct author
        assert f"By {correct_author}</p>" in front_matter, "Front matter should use correct author"

        # Should include logo
        assert "logo_horizontal.png" in front_matter, "Front matter should include logo"

    def test_complete_book_structure(self, structure_generator):
        """generate_complete_book_structure should create full book."""
        story_content = "<div><p>Story content here</p></div>"
        complete_book = structure_generator.generate_complete_book_structure(story_content)

        # Should include all major sections
        assert 'class="front-cover-page"' in complete_book, "Should include front cover"
        assert 'class="explicit-title-page"' in complete_book, "Should include title page"
        assert 'class="publication-info"' in complete_book, "Should include publication info"
        assert 'class="back-cover-page"' in complete_book, "Should include back cover"

        # Should include story content
        assert "Story content here" in complete_book, "Should include story content"

    def test_book_structure_is_valid_html(self, structure_generator):
        """Generated HTML should have proper structure."""
        story_content = "<div><p>Test</p></div>"
        complete_book = structure_generator.generate_complete_book_structure(story_content)

        # Count page-spreads (should have at least 4: front cover, title, pub info, back cover)
        page_spread_count = complete_book.count('class="page-spread"')
        assert page_spread_count >= 4, (
            f"Should have at least 4 page-spreads, found {page_spread_count}"
        )


class TestRegressions:
    def test_regression_subtitle_none_not_displayed(self, test_output_dir):
        """Regression: Ensure 'None' subtitle doesn't display (was bug)."""
        metadata = {
            "title": "The Magic of YET",
            "subtitle": None,
            "author": "FableFlow",
            "publisher": "FableFlow Publishing",
        }

        structure_gen = BookStructureGenerator(test_output_dir, metadata)
        front_cover = structure_gen.generate_front_cover_html()

        # Should not show "None" text
        assert ">None<" not in front_cover, "Should not display 'None' as subtitle"
        assert "subtitle>None<" not in front_cover, "Should not show None in subtitle tags"

    def test_regression_author_fableflow_corrected(self, test_output_dir, correct_author):
        """Regression: Ensure author is correct, not 'FableFlow' (was bug)."""
        metadata = {
            "title": "Test Book",
            "author": "FableFlow",  # This was showing up incorrectly
            "publisher": "FableFlow Publishing",
        }

        structure_gen = BookStructureGenerator(test_output_dir, metadata)
        front_cover = structure_gen.generate_front_cover_html()

        # Should use correct author, not 'FableFlow'
        assert f"By {correct_author}</p>" in front_cover, (
            f"Should use correct author '{correct_author}', not 'FableFlow'"
        )
        # Make sure it's not showing FableFlow as author (unless that IS the correct author)
        if correct_author != "FableFlow":
            assert "By FableFlow</p>" not in front_cover, "Should not show 'FableFlow' as author"

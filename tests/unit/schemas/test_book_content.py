from __future__ import annotations

import json
from pathlib import Path

import pytest

from fable_flow.schemas.book_content import (
    BookContent,
    BookMetadata,
    Chapter,
    IllustrationSpec,
)


class TestIllustrationSpec:
    """Tests for IllustrationSpec."""

    def test_valid_illustration_spec(self):
        spec = IllustrationSpec(
            page=4,
            placement="full_page",
            description="Cassie looking out window at sunrise",
            characters=["Cassie"],
            scene_context="morning, bedroom, excited",
        )
        assert spec.page == 4
        assert spec.placement == "full_page"
        assert len(spec.characters) == 1
        assert spec.image_path is None

    def test_illustration_with_image_path(self):
        spec = IllustrationSpec(
            page=5,
            placement="inline",
            description="Beach scene",
            scene_context="beach, sunny",
            image_path="illustrations/chapter_1_page_5.png",
        )
        assert spec.image_path == "illustrations/chapter_1_page_5.png"


class TestChapter:
    """Tests for Chapter."""

    def test_valid_chapter(self):
        chapter = Chapter(
            number=1,
            title="Morning Excitement",
            text="Cassie woke up early...",
            page_start=3,
            page_end=6,
        )
        assert chapter.number == 1
        assert chapter.title == "Morning Excitement"
        assert len(chapter.illustrations) == 0

    def test_chapter_with_illustrations(self):
        illustration = IllustrationSpec(
            page=4,
            placement="full_page",
            description="Test illustration",
            scene_context="test",
        )
        chapter = Chapter(
            number=1,
            title="Test Chapter",
            text="Test text",
            page_start=1,
            page_end=5,
            illustrations=[illustration],
        )
        assert len(chapter.illustrations) == 1
        assert chapter.illustrations[0].page == 4


class TestBookMetadata:
    """Tests for BookMetadata."""

    def test_valid_metadata(self):
        metadata = BookMetadata(
            title="Cassie's Beach Adventure",
            series="Curious Cassie",
            volume=1,
            target_age=6,
            page_count=24,
            genre="educational adventure",
        )
        assert metadata.title == "Cassie's Beach Adventure"
        assert metadata.series == "Curious Cassie"
        assert metadata.volume == 1

    def test_metadata_without_series(self):
        metadata = BookMetadata(
            title="Standalone Book",
            target_age=7,
            page_count=32,
            genre="fantasy",
        )
        assert metadata.series is None
        assert metadata.volume is None
        assert metadata.author == "FableFlow AI"


class TestBookContent:
    """Tests for BookContent."""

    @pytest.fixture
    def sample_book_content(self):
        """Sample book content for testing."""
        return {
            "metadata": {
                "title": "Test Book",
                "target_age": 6,
                "page_count": 24,
                "genre": "adventure",
            },
            "chapters": [
                {
                    "number": 1,
                    "title": "Chapter One",
                    "text": "This is chapter one text.",
                    "page_start": 3,
                    "page_end": 8,
                    "illustrations": [
                        {
                            "page": 4,
                            "placement": "full_page",
                            "description": "Opening scene",
                            "scene_context": "morning, home",
                        }
                    ],
                },
                {
                    "number": 2,
                    "title": "Chapter Two",
                    "text": "This is chapter two text.",
                    "page_start": 9,
                    "page_end": 15,
                },
            ],
            "full_text": "This is chapter one text. This is chapter two text.",
            "characters_used": ["Cassie", "Caleb"],
        }

    def test_valid_book_content(self, sample_book_content):
        book = BookContent.model_validate(sample_book_content)
        assert book.metadata.title == "Test Book"
        assert len(book.chapters) == 2
        assert book.chapters[0].number == 1
        assert len(book.chapters[0].illustrations) == 1
        assert len(book.characters_used) == 2

    def test_from_json_file(self, tmp_path, sample_book_content):
        json_file = tmp_path / "book_content.json"
        with open(json_file, "w") as f:
            json.dump(sample_book_content, f)

        book = BookContent.from_json_file(json_file)
        assert book.metadata.title == "Test Book"
        assert len(book.chapters) == 2

    def test_to_json_file(self, tmp_path, sample_book_content):
        book = BookContent.model_validate(sample_book_content)
        json_file = tmp_path / "output.json"

        book.to_json_file(json_file)

        assert json_file.exists()
        with open(json_file) as f:
            data = json.load(f)
        assert data["metadata"]["title"] == "Test Book"
        assert len(data["chapters"]) == 2

    def test_round_trip_json(self, tmp_path, sample_book_content):
        book1 = BookContent.model_validate(sample_book_content)
        json_file = tmp_path / "test.json"

        book1.to_json_file(json_file)
        book2 = BookContent.from_json_file(json_file)

        assert book1.model_dump() == book2.model_dump()

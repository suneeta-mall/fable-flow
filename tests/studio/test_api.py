"""Tests for the FableFlow Studio FastAPI backend.

Skipped automatically when the optional `studio` dependency group is not
installed (``uv sync --group studio``).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

import studio.api as api  # noqa: E402

MINIMAL_BOOK = {
    "metadata": {"title": "Test Book", "target_age": 7, "page_count": 10, "genre": "adventure"},
    "chapters": [
        {
            "number": 1,
            "title": "One",
            "text": "Once upon a time there was a curious child.",
            "page_start": 3,
            "page_end": 5,
            "illustrations": [],
        }
    ],
    "full_text": "Once upon a time there was a curious child.",
    "characters_used": ["Cassie"],
}


class FakeModel:
    """Stand-in for EnhancedTextModel; returns a canned reply."""

    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.calls: list[tuple[str, str]] = []

    async def generate(
        self, prompt: str, system: str, temperature: float | None = None, max_tokens=None
    ) -> str:
        self.calls.append((prompt, system))
        return self.reply


@pytest.fixture
def project_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "output"
    proj = root / "test_book"
    proj.mkdir(parents=True)
    (proj / "book_content.json").write_text(json.dumps(MINIMAL_BOOK), encoding="utf-8")
    (proj / "front_cover.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    (root / "empty_dir").mkdir()  # no book_content.json -> ignored
    monkeypatch.setenv("STUDIO_OUTPUT_ROOT", str(root))
    return root


@pytest.fixture
def client(project_root: Path) -> TestClient:
    return TestClient(api.app)


def test_health_reports_output_root(client: TestClient, project_root: Path) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["output_root"] == str(project_root.resolve())


def test_list_projects_discovers_book_and_ignores_empty(client: TestClient) -> None:
    projects = client.get("/api/projects").json()
    assert len(projects) == 1
    assert projects[0]["id"] == "test_book"
    assert projects[0]["title"] == "Test Book"
    assert projects[0]["n_chapters"] == 1


def test_get_book_roundtrips(client: TestClient) -> None:
    book = client.get("/api/book", params={"project": "test_book"}).json()
    assert book["metadata"]["title"] == "Test Book"


def test_get_book_missing_project_404(client: TestClient) -> None:
    assert client.get("/api/book", params={"project": "nope"}).status_code == 404


def test_save_valid_book_writes_backup(client: TestClient, project_root: Path) -> None:
    book = dict(MINIMAL_BOOK)
    book["metadata"] = {**MINIMAL_BOOK["metadata"], "title": "Edited Title"}
    resp = client.post("/api/book", params={"project": "test_book"}, json=book)
    assert resp.status_code == 200

    saved = json.loads((project_root / "test_book" / "book_content.json").read_text())
    assert saved["metadata"]["title"] == "Edited Title"
    bak = json.loads((project_root / "test_book" / "book_content.json.bak").read_text())
    assert bak["metadata"]["title"] == "Test Book"


def test_save_invalid_book_returns_422(client: TestClient) -> None:
    resp = client.post("/api/book", params={"project": "test_book"}, json={"metadata": {}})
    assert resp.status_code == 422
    assert isinstance(resp.json()["detail"], list)


def test_media_serves_existing_file(client: TestClient) -> None:
    resp = client.get("/api/media", params={"project": "test_book", "path": "front_cover.png"})
    assert resp.status_code == 200


def test_media_path_traversal_rejected(client: TestClient) -> None:
    resp = client.get("/api/media", params={"project": "test_book", "path": "../../etc/passwd"})
    assert resp.status_code == 400


def test_media_serves_output_root_relative_path(client: TestClient, project_root: Path) -> None:
    """book_content.json produced by `make run` stores output-root-relative paths."""
    img = project_root / "test_book" / "illustrations" / "chapter_1_ill_1.png"
    img.parent.mkdir(parents=True, exist_ok=True)
    img.write_bytes(b"\x89PNG\r\n\x1a\n")
    # the path as the producer stores it: output/<project>/illustrations/...
    resp = client.get(
        "/api/media",
        params={
            "project": "test_book",
            "path": "output/test_book/illustrations/chapter_1_ill_1.png",
        },
    )
    assert resp.status_code == 200


def test_improve_returns_text(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(api, "_text_model", lambda: FakeModel("A polished passage."))
    resp = client.post(
        "/api/ai/improve",
        json={"action": "polish_prose", "text": "raw", "context": {"target_age": 7}},
    )
    assert resp.status_code == 200
    assert resp.json()["result"] == "A polished passage."


def test_improve_unknown_action_400(client: TestClient) -> None:
    resp = client.post("/api/ai/improve", json={"action": "bogus", "text": "x"})
    assert resp.status_code == 400


def test_improve_list_action_parses_to_list(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    reply = '["Why did Cassie wonder?", "What would you ask?", "How did it feel?"]'
    monkeypatch.setattr(api, "_text_model", lambda: FakeModel(reply))
    resp = client.post(
        "/api/ai/improve",
        json={"action": "reflection_questions", "text": "chapter text", "context": {}},
    )
    result = resp.json()["result"]
    assert isinstance(result, list) and len(result) == 3


def test_chat_uses_book_context(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    model = FakeModel("Here is some feedback.")
    monkeypatch.setattr(api, "_text_model", lambda: model)
    resp = client.post(
        "/api/ai/chat", json={"project": "test_book", "message": "How is chapter 1?"}
    )
    assert resp.status_code == 200
    assert resp.json()["response"] == "Here is some feedback."
    # the book title should have been folded into the system prompt
    assert "Test Book" in model.calls[0][1]


def test_publish_invokes_publishers(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, project_root: Path
) -> None:
    calls: list[str] = []

    def fake_pdf(book, out: Path) -> Path:
        calls.append("pdf")
        Path(out).write_bytes(b"%PDF")
        return Path(out)

    def fake_epub(book, out: Path) -> Path:
        calls.append("epub")
        Path(out).write_bytes(b"PK")
        return Path(out)

    monkeypatch.setattr(api, "generate_pdf", fake_pdf)
    monkeypatch.setattr(api, "generate_epub", fake_epub)

    resp = client.post("/api/publish", params={"project": "test_book"}, json={"formats": ["pdf"]})
    assert resp.status_code == 200
    assert calls == ["pdf"]
    assert resp.json()["outputs"] == {"pdf": "test_book.pdf"}

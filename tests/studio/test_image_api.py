"""Tests for Studio's image regenerate/accept/discard endpoints.

The image model is mocked, so these run without torch/diffusers/a GPU. The flow
is non-destructive: regenerate writes a candidate, accept promotes it, discard
deletes it.
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
            "text": "text",
            "page_start": 3,
            "page_end": 5,
            "illustrations": [],
        }
    ],
    "full_text": "text",
    "characters_used": ["Cassie"],
}

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
TARGET = "illustrations/chapter_1_ill_1.png"
CANDIDATE = "illustrations/.studio_candidate_chapter_1_ill_1.png"


class FakeImageModel:
    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.released = False

    async def generate_image(self, prompt, width, height, seed=None, negative_prompt=None) -> bytes:
        self.calls.append({"kind": "text", "prompt": prompt})
        return PNG_MAGIC + b"NEW"

    async def generate_with_reference(
        self, prompt, reference_image_path, width, height, seed=None, negative_prompt=None
    ) -> bytes:
        self.calls.append({"kind": "ref", "ref": reference_image_path})
        return PNG_MAGIC + b"NEWREF"

    def release(self) -> None:
        self.released = True


@pytest.fixture
def project_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "output"
    proj = root / "test_book"
    (proj / "illustrations").mkdir(parents=True)
    (proj / "book_content.json").write_text(json.dumps(MINIMAL_BOOK), encoding="utf-8")
    monkeypatch.setenv("STUDIO_OUTPUT_ROOT", str(root))
    return root


@pytest.fixture
def client(project_root: Path) -> TestClient:
    return TestClient(api.app)


def test_regenerate_writes_candidate_and_leaves_target_untouched(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, project_root: Path
) -> None:
    monkeypatch.setattr(api, "_image_model", lambda: FakeImageModel())
    proj = project_root / "test_book"
    (proj / TARGET).write_bytes(PNG_MAGIC + b"OLD")

    resp = client.post(
        "/api/image/regenerate",
        params={"project": "test_book"},
        json={"target": TARGET, "prompt": "A curious child by the sea", "target_age": 7},
    )
    assert resp.status_code == 200
    assert resp.json()["candidate"] == CANDIDATE
    # candidate written, live image unchanged
    assert (proj / CANDIDATE).read_bytes() == PNG_MAGIC + b"NEW"
    assert (proj / TARGET).read_bytes() == PNG_MAGIC + b"OLD"


def test_regenerate_uses_reference_when_requested(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, project_root: Path
) -> None:
    fake = FakeImageModel()
    monkeypatch.setattr(api, "_image_model", lambda: fake)
    (project_root / "test_book" / TARGET).write_bytes(PNG_MAGIC + b"OLD")

    resp = client.post(
        "/api/image/regenerate",
        params={"project": "test_book"},
        json={"target": TARGET, "prompt": "edit it", "use_current_as_reference": True},
    )
    assert resp.status_code == 200
    assert fake.calls[0]["kind"] == "ref"


def test_accept_promotes_candidate(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, project_root: Path
) -> None:
    monkeypatch.setattr(api, "_image_model", lambda: FakeImageModel())
    proj = project_root / "test_book"
    client.post(
        "/api/image/regenerate",
        params={"project": "test_book"},
        json={"target": TARGET, "prompt": "x"},
    )
    resp = client.post(
        "/api/image/accept",
        params={"project": "test_book"},
        json={"candidate": CANDIDATE, "target": TARGET},
    )
    assert resp.status_code == 200
    # producer-style path: <output_root>/<project>/<rel>
    assert resp.json()["image_path"].endswith(f"test_book/{TARGET}")
    assert (proj / TARGET).read_bytes() == PNG_MAGIC + b"NEW"
    assert not (proj / CANDIDATE).exists()  # candidate consumed


def test_discard_removes_candidate(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, project_root: Path
) -> None:
    monkeypatch.setattr(api, "_image_model", lambda: FakeImageModel())
    proj = project_root / "test_book"
    client.post(
        "/api/image/regenerate",
        params={"project": "test_book"},
        json={"target": TARGET, "prompt": "x"},
    )
    assert (proj / CANDIDATE).exists()
    resp = client.post(
        "/api/image/discard", params={"project": "test_book"}, json={"candidate": CANDIDATE}
    )
    assert resp.status_code == 200
    assert not (proj / CANDIDATE).exists()


def test_accept_missing_candidate_404(client: TestClient) -> None:
    resp = client.post(
        "/api/image/accept",
        params={"project": "test_book"},
        json={"candidate": CANDIDATE, "target": TARGET},
    )
    assert resp.status_code == 404


def test_regenerate_target_traversal_rejected(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(api, "_image_model", lambda: FakeImageModel())
    resp = client.post(
        "/api/image/regenerate",
        params={"project": "test_book"},
        json={"target": "../escape.png", "prompt": "x"},
    )
    assert resp.status_code == 400


def test_release_when_not_loaded(client: TestClient) -> None:
    assert client.post("/api/image/release").json()["status"] == "not_loaded"

"""FastAPI backend for FableFlow Studio.

A separate service from the production pipeline in producer/fable_flow/. It
discovers the book_content.json artifacts the producer writes under the output
root, serves them to the Studio editor for structured editing, validates and
saves edits back, runs AI improvement/chat through the project's own
``EnhancedTextModel``, and can re-render PDF/EPUB from edited content.

Run with:  uv run uvicorn studio.api:app --reload --port 8077
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path, PurePosixPath
from typing import Any

import openai
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from loguru import logger
from pydantic import BaseModel, Field, ValidationError

from fable_flow.agents._json_parse import parse_json_response
from fable_flow.config import config
from fable_flow.models.text import EnhancedTextModel
from fable_flow.publishers import generate_epub, generate_pdf
from fable_flow.schemas.book_content import BookContent, IllustrationSpec
from studio.ai_actions import ACTIONS

BOOK_FILE = "book_content.json"
# Default off 8000 on purpose: that port is the project's conventional LLM
# server (vLLM / config default model URL). Sharing it makes Studio intercept
# its own model requests and 404. Override with STUDIO_PORT.
DEFAULT_STUDIO_PORT = 8077


def _output_root() -> Path:
    """Resolve the output root fresh each call so tests can override the env var."""
    return Path(os.getenv("STUDIO_OUTPUT_ROOT", "output")).resolve()


_text_model_singleton: EnhancedTextModel | None = None
_image_model_singleton: Any = None


def _text_model() -> EnhancedTextModel:
    global _text_model_singleton
    if _text_model_singleton is None:
        _text_model_singleton = EnhancedTextModel()
    return _text_model_singleton


def _image_model() -> Any:
    """Lazily load the configured image model (config.model.image_generation).

    The diffusers/torch import and pipeline load are deferred to the first image
    edit so plain text editing never pays the GPU/VRAM cost. Kept loaded across
    requests; free it with POST /api/image/release.
    """
    global _image_model_singleton
    if _image_model_singleton is None:
        from fable_flow.models.image import EnhancedImageModel  # heavy: torch + diffusers

        logger.info(f"Studio: loading image model {config.model.image_generation.model}…")
        _image_model_singleton = EnhancedImageModel()
    return _image_model_singleton


async def _run_model(prompt: str, system: str, temperature: float) -> str:
    """Call the configured LLM, surfacing connection/HTTP failures as 502s.

    The model endpoint comes from config.yaml (config.model.server.url) — the
    same one the producer uses. A bad URL, an unreachable server, or a 404 on
    the chat-completions route raises a clear error pointing at MODEL_SERVER_URL
    rather than a bare 500.
    """
    try:
        return await _text_model().generate(prompt, system, temperature=temperature)
    except openai.OpenAIError as e:
        raise HTTPException(
            status_code=502,
            detail=(
                f"LLM request to {config.model.server.url} "
                f"(model={config.model.default}) failed: {e}. "
                "Check MODEL_SERVER_URL / config.yaml and that the model server is running."
            ),
        ) from e


def _project_dir(project: str) -> Path:
    """Resolve a project id to its directory, guarding against path traversal.

    Raises:
        HTTPException: 400 if the path escapes the output root, 404 if the
            project directory or its book_content.json does not exist.
    """
    root = _output_root()
    candidate = (root / project).resolve()
    if not candidate.is_relative_to(root):
        raise HTTPException(status_code=400, detail=f"Invalid project path: {project!r}")
    if not (candidate / BOOK_FILE).is_file():
        raise HTTPException(status_code=404, detail=f"No {BOOK_FILE} for project: {project!r}")
    return candidate


def _project_rel(proj_dir: Path, path: str) -> str:
    """Map a stored asset path to its in-project relative location.

    The producer stores image paths as ``<output_root>/<project>/illustrations/..``
    (e.g. ``output/cassie_fei_fei_li_input/illustrations/ch1.png``) — relative to
    its CWD, not to the project dir. The actual file lives inside the project dir,
    so we strip everything up to and including the LAST occurrence of the project
    dir name, leaving the true in-project path. Paths containing ``..`` are
    rejected (400). A bare in-project path is returned unchanged.
    """
    parts = [p for p in PurePosixPath(path.replace("\\", "/")).parts if p != "/"]
    if ".." in parts:
        raise HTTPException(status_code=400, detail=f"Invalid path: {path!r}")
    if proj_dir.name in parts:
        last = max(i for i, p in enumerate(parts) if p == proj_dir.name)
        parts = parts[last + 1 :]
    return "/".join(parts)


def _stored_path(project: str, rel: str) -> str:
    """Reproduce the producer's image_path style: ``<output_root>/<project>/<rel>``.

    Uses the raw STUDIO_OUTPUT_ROOT value (default ``output``) so paths the studio
    writes match what the pipeline writes and stay compatible with ``--resume``.
    """
    root = os.getenv("STUDIO_OUTPUT_ROOT", "output").rstrip("/")
    return f"{root}/{project}/{rel}"


def _candidate_rel(target: str) -> str:
    """Sibling path for a not-yet-accepted image, e.g. illustrations/.studio_candidate_ch1.png."""
    p = PurePosixPath(target)
    return str(p.parent / f".studio_candidate_{p.name}")


def _safe_filename(title: str) -> str:
    cleaned = "".join(c if c.isalnum() or c in (" ", "-", "_") else "_" for c in title)
    return cleaned.strip().lower().replace(" ", "_")[:80] or "fableflow_book"


def _book_summary(data: dict[str, Any]) -> str:
    """Compact, bounded text summary of a book for chat grounding."""
    meta = data.get("metadata", {})
    lines = [
        f"Title: {meta.get('title')}",
        f"Target age: {meta.get('target_age')}",
        f"Genre: {meta.get('genre')}",
        f"Characters: {', '.join(data.get('characters_used', []))}",
        "Chapters:",
    ]
    for ch in data.get("chapters", []):
        excerpt = " ".join((ch.get("text") or "").split())[:200]
        lines.append(f"  {ch.get('number')}. {ch.get('title')} — {excerpt}…")
    return "\n".join(lines)


class ImproveRequest(BaseModel):
    action: str
    text: str
    context: dict[str, Any] = Field(default_factory=dict)
    temperature: float = 0.7


class ImproveResponse(BaseModel):
    result: str | list[str]


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    project: str
    message: str
    history: list[ChatMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    response: str


class PublishRequest(BaseModel):
    formats: list[str] = Field(default_factory=lambda: ["pdf", "epub"])


class ImageRegenRequest(BaseModel):
    """Regenerate one illustration with the configured image model.

    The client sends the (possibly unsaved) prompt and scene fields; the server
    only writes the PNG and returns its relative path. book_content.json is left
    alone so it can't clobber the client's working copy — the new image_path is
    persisted on the next normal Save.
    """

    target: str = Field(
        ..., description="Project-relative path to write, e.g. illustrations/ch1.png"
    )
    prompt: str
    scene_context: str = ""
    characters: list[str] = Field(default_factory=list)
    target_age: int = 7
    reference_path: str | None = Field(
        None, description="Project-relative reference image for character/style conditioning"
    )
    use_current_as_reference: bool = Field(
        False, description="Condition on the existing image at `target` (image-to-image edit)"
    )
    seed: int | None = None


class ImageAcceptRequest(BaseModel):
    candidate: str
    target: str


class ImageDiscardRequest(BaseModel):
    candidate: str


app = FastAPI(
    title="FableFlow Studio API",
    description="Structured editor + AI assist for book_content.json. Separate from the pipeline.",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "healthy",
        "service": "fableflow-studio",
        "output_root": str(_output_root()),
        "model_server_url": config.model.server.url,
        "default_model": config.model.default,
        "image_model": config.model.image_generation.model,
    }


@app.get("/api/actions")
def list_actions() -> dict[str, dict[str, str]]:
    """Catalogue of AI actions, grouped by field family, for the UI to render."""
    return {
        name: {"label": a.label, "field": a.field, "returns_list": str(a.returns_list)}
        for name, a in ACTIONS.items()
    }


@app.get("/api/projects")
def list_projects() -> list[dict[str, Any]]:
    """List every directory under the output root that contains a book_content.json."""
    root = _output_root()
    projects: list[dict[str, Any]] = []
    if not root.exists():
        return projects
    for book_path in sorted(root.rglob(BOOK_FILE)):
        proj_dir = book_path.parent
        rel = proj_dir.relative_to(root).as_posix()
        try:
            data = json.loads(book_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Skipping unreadable {book_path}: {e}")
            continue
        meta = data.get("metadata", {})
        cover = data.get("cover") or {}
        projects.append(
            {
                "id": rel,
                "title": meta.get("title", rel),
                "series": meta.get("series"),
                "target_age": meta.get("target_age"),
                "page_count": meta.get("page_count"),
                "genre": meta.get("genre"),
                "n_chapters": len(data.get("chapters", [])),
                "has_pdf": any(proj_dir.glob("*.pdf")),
                "has_epub": any(proj_dir.glob("*.epub")),
                "cover": cover.get("front_path"),
            }
        )
    return projects


@app.get("/api/book")
def get_book(project: str = Query(...)) -> dict[str, Any]:
    book_path = _project_dir(project) / BOOK_FILE
    return json.loads(book_path.read_text(encoding="utf-8"))


@app.post("/api/book")
def save_book(payload: dict[str, Any], project: str = Query(...)) -> dict[str, Any]:
    """Validate the edited document against BookContent and persist it.

    A timestamp-free ``.bak`` of the previous version is written before saving.
    Invalid documents are rejected with 422 and the pydantic error list.
    """
    proj_dir = _project_dir(project)
    try:
        book = BookContent.model_validate(payload)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=json.loads(e.json())) from e

    book_path = proj_dir / BOOK_FILE
    shutil.copy2(book_path, book_path.with_suffix(".json.bak"))
    book.to_json_file(book_path)
    return {"status": "saved", "project": project}


@app.get("/api/media")
def get_media(project: str = Query(...), path: str = Query(...)) -> FileResponse:
    proj_dir = _project_dir(project)
    target = proj_dir / _project_rel(proj_dir, path)
    if not target.is_file():
        raise HTTPException(status_code=404, detail=f"Media not found: {path!r}")
    return FileResponse(target)


@app.post("/api/ai/improve", response_model=ImproveResponse)
async def improve(req: ImproveRequest) -> ImproveResponse:
    action = ACTIONS.get(req.action)
    if action is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown action {req.action!r}. Known: {sorted(ACTIONS)}",
        )
    raw = await _run_model(
        action.template(req.text, req.context),
        action.system,
        req.temperature,
    )
    if action.returns_list:
        return ImproveResponse(result=parse_json_response(raw, expect=list))
    return ImproveResponse(result=raw.strip())


@app.post("/api/ai/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    proj_dir = _project_dir(req.project)
    data = json.loads((proj_dir / BOOK_FILE).read_text(encoding="utf-8"))
    system = (
        "You are a friendly, expert children's book editor helping an author improve "
        "their book. Be concise, concrete, and age-appropriate. When you propose text, "
        "keep it ready to paste into the manuscript.\n\n"
        f"BOOK CONTEXT:\n{_book_summary(data)}"
    )
    history = "\n".join(f"{m.role}: {m.content}" for m in req.history[-8:])
    prompt = (f"{history}\n\n" if history else "") + f"Author: {req.message}"
    reply = await _run_model(prompt, system, temperature=0.7)
    return ChatResponse(response=reply.strip())


@app.post("/api/publish")
def publish(payload: PublishRequest, project: str = Query(...)) -> dict[str, Any]:
    """Re-render PDF/EPUB from the saved book_content.json. CPU-only, no models."""
    proj_dir = _project_dir(project)
    book = BookContent.from_json_file(proj_dir / BOOK_FILE)
    slug = _safe_filename(book.metadata.title)
    outputs: dict[str, str] = {}
    if "pdf" in payload.formats:
        out = proj_dir / f"{slug}.pdf"
        generate_pdf(book, out)
        outputs["pdf"] = out.name
    if "epub" in payload.formats:
        out = proj_dir / f"{slug}.epub"
        generate_epub(book, out)
        outputs["epub"] = out.name
    return {"status": "published", "outputs": outputs}


@app.post("/api/image/regenerate")
async def regenerate_image(payload: ImageRegenRequest, project: str = Query(...)) -> dict[str, str]:
    """Render a CANDIDATE illustration without touching the live image.

    Reuses the producer's prompt composition (`build_scene_prompt`) and config
    style, so studio-edited images match pipeline output. The PNG is written to a
    sibling candidate path; the client previews current-vs-candidate and then
    calls /api/image/accept (promote) or /api/image/discard (delete).
    """
    proj_dir = _project_dir(project)
    target_rel = _project_rel(proj_dir, payload.target)
    target_path = proj_dir / target_rel
    candidate_rel = _candidate_rel(target_rel)
    candidate_path = proj_dir / candidate_rel
    candidate_path.parent.mkdir(parents=True, exist_ok=True)

    from fable_flow.agents._image_prompts import build_negative_prompt, build_scene_prompt

    spec = IllustrationSpec(
        page=1,
        placement="inline",
        description=payload.prompt,
        scene_context=payload.scene_context or "illustration scene",
        characters=payload.characters,
    )
    full_prompt = build_scene_prompt(spec, [], config.style.illustration_style, None)
    negative = build_negative_prompt(payload.target_age)

    reference: str | None = None
    if payload.reference_path:
        reference = str(proj_dir / _project_rel(proj_dir, payload.reference_path))
    elif payload.use_current_as_reference and target_path.is_file():
        reference = str(target_path)

    try:
        model = _image_model()
        if reference:
            img_bytes = await model.generate_with_reference(
                prompt=full_prompt,
                reference_image_path=reference,
                width=1024,
                height=1024,
                seed=payload.seed,
                negative_prompt=negative,
            )
        else:
            img_bytes = await model.generate_image(
                prompt=full_prompt,
                width=1024,
                height=1024,
                seed=payload.seed,
                negative_prompt=negative,
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image generation failed: {e}") from e

    candidate_path.write_bytes(img_bytes)
    return {"candidate": candidate_rel, "prompt": full_prompt}


@app.post("/api/image/accept")
def accept_image(payload: ImageAcceptRequest, project: str = Query(...)) -> dict[str, str]:
    """Promote a candidate to its target path (overwriting the live image)."""
    proj_dir = _project_dir(project)
    candidate_path = proj_dir / _project_rel(proj_dir, payload.candidate)
    target_rel = _project_rel(proj_dir, payload.target)
    target_path = proj_dir / target_rel
    if not candidate_path.is_file():
        raise HTTPException(status_code=404, detail=f"No candidate at {payload.candidate!r}")
    target_path.parent.mkdir(parents=True, exist_ok=True)
    candidate_path.replace(target_path)
    return {"image_path": _stored_path(project, target_rel)}


@app.post("/api/image/discard")
def discard_image(payload: ImageDiscardRequest, project: str = Query(...)) -> dict[str, str]:
    """Delete a rejected candidate. Safe if it's already gone."""
    proj_dir = _project_dir(project)
    candidate_path = proj_dir / _project_rel(proj_dir, payload.candidate)
    candidate_path.unlink(missing_ok=True)
    return {"status": "discarded"}


@app.post("/api/image/release")
def release_image_model() -> dict[str, str]:
    """Free image-model VRAM. Safe to call when nothing is loaded."""
    global _image_model_singleton
    if _image_model_singleton is None:
        return {"status": "not_loaded"}
    _image_model_singleton.release()
    _image_model_singleton = None
    return {"status": "released"}


def main() -> None:
    import uvicorn

    uvicorn.run(
        "studio.api:app",
        host=os.getenv("STUDIO_HOST", "0.0.0.0"),
        port=int(os.getenv("STUDIO_PORT", str(DEFAULT_STUDIO_PORT))),
        reload=bool(os.getenv("STUDIO_RELOAD")),
    )


if __name__ == "__main__":
    main()

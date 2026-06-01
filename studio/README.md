# FableFlow Studio

A lightweight web editor for the **`book_content.json`** artifacts the FableFlow
producer writes. It pairs with producer outputs: every folder under the output
root that contains a `book_content.json` shows up as a project you can edit in a
structured, form-based UI — with AI assistance for improving the content.

Studio is **independent** from the production pipeline in `producer/fable_flow/`.
For text work it only reuses the project's `EnhancedTextModel` (AI improve/chat)
and the `publishers` (to re-render PDF/EPUB). Image editing is opt-in: the first
time you regenerate an illustration, Studio lazily loads the **image model from
`config.yaml`** (`model.image_generation.model`) — the same one the producer
uses — so plain text editing never pays the GPU/VRAM cost.

## Quick start

```bash
make studio-install   # uv sync --group studio  +  npm install
make studio-start     # FastAPI on :8000, Vite UI on :3000
make studio-stop
```

Open **http://localhost:3000**.

- Frontend: http://localhost:3000
- Backend API: http://localhost:8077 (Swagger at `/docs`)

> The backend defaults to **8077**, not 8000 — port 8000 is the project's
> conventional LLM server (vLLM / the `config.yaml` default model URL). Sharing
> it would make Studio intercept its own model requests. Override with
> `STUDIO_PORT` if needed (and update the Vite proxy in `web-ui/vite.config.js`).

The output root defaults to `output/`. Point it elsewhere with
`STUDIO_OUTPUT_ROOT=/path/to/output`.

## What you can do

- **Browse** every generated book (cover thumbnail, chapter count, PDF/EPUB badges).
- **Edit structurally**: metadata, per-chapter title/text/poem/page-range,
  reflection questions, illustration specs (description, caption, placement,
  characters, with image preview), the experiment, the biography, and back matter.
- **Improve with AI**: every text field has an **✨ Improve** menu (polish, tighten,
  fit-the-age, refine poem, suggest reflection questions, improve image prompt,
  write caption, suggest tagline/premise, …). The model *proposes* — you review a
  word-level diff and **Accept or Reject**. AI never overwrites silently.
- **Edit illustrations**: each illustration card has a **Generate/Regenerate**
  button that renders the image with the `config.yaml` image model from its
  (AI-improvable) description. The result opens in a **side-by-side modal —
  current vs. new candidate** — so you can compare before committing:
  **Accept** promotes the candidate to the live image (its `image_path` is
  persisted on the next Save); **Reject** discards it. The live image is never
  overwritten until you Accept. Tick *use as reference* to make it an
  image-to-image edit from the current picture.
- **Chat** with a book-scoped editor assistant (bottom-right).
- **Raw JSON** escape-hatch tab (Monaco) for anything the forms don't cover.
- **Re-publish** the PDF/EPUB from edited content (CPU-only, no models loaded).

Saving validates the whole document against the `BookContent` schema; invalid
edits are rejected with field-level errors and nothing is written. A `.bak` of
the previous version is kept next to the file.

## Architecture

```
studio/
├── api.py          # FastAPI backend (reuses fable_flow schemas/model/publishers)
├── ai_actions.py   # registry of AI improvement actions (action -> prompts)
└── web-ui/         # Vite + React + Tailwind SPA
    └── src/
        ├── pages/      ProjectBrowser, BookEditor
        ├── components/ Metadata/Chapter/Illustration/Experiment/Biography panels,
        │               ImproveMenu, DiffModal, ChatPanel, RawJsonTab, ui primitives
        └── services/   api.js
```

The Vite dev server proxies `/api` to the backend on `:8000`.

## API reference

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | liveness + resolved output root |
| GET | `/api/actions` | AI action catalogue (grouped by field family) |
| GET | `/api/projects` | list books under the output root |
| GET | `/api/book?project=` | load a book's JSON |
| POST | `/api/book?project=` | validate (`BookContent`) and save; 422 on invalid |
| GET | `/api/media?project=&path=` | serve an illustration/cover image |
| POST | `/api/ai/improve` | `{action, text, context}` → improved text/list |
| POST | `/api/ai/chat` | `{project, message, history}` → reply |
| POST | `/api/publish?project=` | re-render `{formats:["pdf","epub"]}` |
| POST | `/api/image/regenerate?project=` | render a candidate illustration → `{candidate}` |
| POST | `/api/image/accept?project=` | promote a candidate to its target → `{image_path}` |
| POST | `/api/image/discard?project=` | delete a rejected candidate |
| POST | `/api/image/release` | free the image model's VRAM |

`/health` reports the resolved output root and the configured model server URL,
default text model, and image model — handy for confirming what AI calls hit.

## Configuration

| Env var | Default | Meaning |
|---------|---------|---------|
| `STUDIO_OUTPUT_ROOT` | `output` | Where to discover book projects |
| `STUDIO_HOST` | `0.0.0.0` | Backend bind host |
| `STUDIO_PORT` | `8077` | Backend port (kept off 8000, the LLM server's port) |
| `STUDIO_RELOAD` | unset | Set to enable uvicorn auto-reload |

AI improve/chat use the same model server as the producer (`MODEL_SERVER_URL`,
`DEFAULT_MODEL`, `MODEL_API_KEY` — see the project `.env`/`config`).

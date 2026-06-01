---
title: Getting Started
---

# Getting Started

Set up FableFlow and generate your first book in three steps.

1. **[Installation](installation.md)** — clone the repo and `make install`, then configure your model server in `.env`.
2. **[Quick Tutorial](quick-start.md)** — validate an example input spec and run the full pipeline with `fable-flow generate`.
3. **[Configuration](configuration.md)** — tune models, styles, and output formats in `config/default.yaml`.

## Prerequisites

- Python 3.13 and Git
- An OpenAI-compatible model server (local vLLM/Ollama or a hosted proxy) for text generation
- A CUDA GPU for image, audio, and video generation

Once installed, the fastest path is:

```bash
fable-flow generate examples/cassie_beach_adventure_input.json
```

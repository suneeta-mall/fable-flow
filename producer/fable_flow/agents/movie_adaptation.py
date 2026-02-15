"""Phase 2 movie adaptation: scene extraction and final movie assembly."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from loguru import logger

from fable_flow.agents._json_parse import parse_json_response
from fable_flow.models import EnhancedTextModel
from fable_flow.schemas.book_content import BookContent
from fable_flow.schemas.scene_manifest import SceneManifest, SceneSpec


class SceneExtractorAgent:
    """Extract scene boundaries from book content for movie adaptation."""

    def __init__(
        self,
        model: str | None = None,
        output_dir: Path | None = None,
        target_scene_duration: float = 6.0,
    ) -> None:
        self._model = EnhancedTextModel(model)
        self.output_dir = output_dir or Path("output")
        self.target_scene_duration = target_scene_duration

    def _estimate_duration(self, text: str, words_per_second: float = 2.5) -> float:
        return len(text.split()) / words_per_second

    def _build_prompt(self, book: BookContent) -> str:
        chapter_summary = "\n".join(
            f'Chapter {ch.number}: "{ch.title}" '
            f"({len(ch.text.split())} words, pages {ch.page_start}-{ch.page_end}, "
            f"{len(ch.illustrations)} illustrations)"
            for ch in book.chapters
        )

        illustration_lines = []
        for ch in book.chapters:
            for ill in ch.illustrations:
                if ill.image_path:
                    illustration_lines.append(
                        f"  - page {ill.page} (chapter {ch.number}): {ill.description[:80]}"
                    )
        illustration_index = "\n".join(illustration_lines) or "  (none rendered)"

        return f"""Extract natural scene boundaries from this book for movie adaptation.

**BOOK:** "{book.metadata.title}"

**STRUCTURE:**
{chapter_summary}

**RENDERED ILLUSTRATIONS (set page_reference to match if scene aligns):**
{illustration_index}

**FULL TEXT:**

{book.full_text}

---

Each scene should:
1. Be a natural narrative unit (setting change, time shift, action sequence)
2. Target ~{self.target_scene_duration} seconds of narration (~15-20 words)
3. Have clear visual potential
4. Include the EXACT text from the book

Return ONLY a JSON array, 10-30 scenes total covering the entire story:

```json
[
  {{
    "id": "ch1_scene01",
    "chapter": 1,
    "sequence": 1,
    "text": "Exact text from book...",
    "page_reference": 4,
    "characters": ["Cassie"],
    "setting": "bedroom",
    "mood": "excited"
  }}
]
```

`page_reference` is the page number of a rendered illustration to reuse, or null. No commentary."""

    async def extract_scenes(self, book: BookContent) -> SceneManifest:
        logger.info(f"SceneExtractorAgent: extracting from '{book.metadata.title}'")
        system = "You are a film adaptation specialist for children's literature."
        prompt = self._build_prompt(book)
        response = await self._model.generate(prompt, system, temperature=0.3)
        raw_scenes = parse_json_response(response, expect=list)

        page_to_illustration = self._build_page_index(book)
        scenes: list[SceneSpec] = []
        for scene_data in raw_scenes:
            page_ref = scene_data.get("page_reference")
            illustration_path = page_to_illustration.get(int(page_ref)) if page_ref else None
            scenes.append(
                SceneSpec(
                    id=scene_data["id"],
                    chapter=int(scene_data["chapter"]),
                    sequence=int(scene_data["sequence"]),
                    text=scene_data["text"],
                    page_reference=int(page_ref) if page_ref else None,
                    characters=scene_data.get("characters", []),
                    setting=scene_data["setting"],
                    mood=scene_data["mood"],
                    illustration_reference=illustration_path,
                    estimated_duration=self._estimate_duration(scene_data["text"]),
                )
            )

        total_duration = sum(s.estimated_duration for s in scenes)
        manifest = SceneManifest(
            book_title=book.metadata.title,
            total_scenes=len(scenes),
            estimated_total_duration=total_duration,
            scenes=scenes,
        )

        logger.info(
            f"SceneExtractorAgent: {len(scenes)} scenes, "
            f"estimated {total_duration:.1f}s "
            f"({sum(1 for s in scenes if s.illustration_reference)} reuse book illustrations)"
        )

        out_file = self.output_dir / "scene_manifest.json"
        out_file.parent.mkdir(parents=True, exist_ok=True)
        manifest.to_json_file(out_file)
        return manifest

    def _build_page_index(self, book: BookContent) -> dict[int, str]:
        index: dict[int, str] = {}
        for ch in book.chapters:
            for ill in ch.illustrations:
                if ill.image_path:
                    index[ill.page] = ill.image_path
        return index


class MovieAssemblerAgent:
    """Concatenate scene composites into the final movie file."""

    def __init__(self, output_dir: Path | None = None) -> None:
        self.output_dir = output_dir or Path("output")

    async def assemble_movie(
        self,
        manifest: SceneManifest,
        output_filename: str = "story_movie.mp4",
        resume: bool = False,
    ) -> str:
        output_path = self.output_dir / output_filename

        if resume and output_path.exists():
            logger.info(f"Resume: skipping movie assembly, {output_path.name} already exists")
            return str(output_path)

        logger.info(f"MovieAssembler: assembling {len(manifest.scenes)} scenes")

        scene_files = [s.composite for s in manifest.scenes if s.composite]
        if not scene_files:
            raise ValueError("No scene composites found in manifest")

        concat_list_path = self.output_dir / "concat_list.txt"
        self._write_concat_file(scene_files, concat_list_path)

        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_list_path),
            "-c",
            "copy",
            str(output_path),
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"ffmpeg concat failed: {stderr.decode(errors='replace')[:1000]}")

        if not output_path.exists():
            raise RuntimeError(f"ffmpeg succeeded but {output_path} missing")

        self._write_movie_manifest(manifest, self.output_dir / "movie_manifest.json")
        logger.info(f"MovieAssembler: wrote {output_path}")
        return str(output_path)

    def _write_concat_file(self, scene_files: list[str], path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            for scene_file in scene_files:
                f.write(f"file '{Path(scene_file).resolve()}'\n")

    def _write_movie_manifest(self, scene_manifest: SceneManifest, path: Path) -> None:
        timecode = 0.0
        chapters = []
        for scene in scene_manifest.scenes:
            if scene.narration:
                chapters.append(
                    {
                        "scene_id": scene.id,
                        "title": f"Chapter {scene.chapter}, Scene {scene.sequence}",
                        "start_time": timecode,
                        "duration": scene.narration.duration,
                    }
                )
                timecode += scene.narration.duration

        data = {
            "movie_title": scene_manifest.book_title,
            "total_duration": timecode,
            "total_scenes": len(chapters),
            "chapters": chapters,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

"""Phase 2 per-scene production: narration → image → video → music → subtitles → composite.

Narration sets the master timing; video and music match its exact duration.
Models are lazy-loaded and released between modalities to fit a single GPU.
"""

from __future__ import annotations

import asyncio
import hashlib
from collections.abc import Callable
from pathlib import Path

from loguru import logger
from PIL import Image

from fable_flow.agents._image_prompts import (
    build_negative_prompt,
    build_scene_prompt_for_movie,
)
from fable_flow.config import config
from fable_flow.schemas.book_content import CharacterReference
from fable_flow.schemas.input_spec import Character
from fable_flow.schemas.scene_manifest import (
    ImageAsset,
    MusicAsset,
    NarrationAsset,
    SceneSpec,
    SubtitleAsset,
    VideoAsset,
)


def _scene_seed(scene_id: str) -> int:
    return int(hashlib.sha1(scene_id.encode("utf-8")).hexdigest()[:8], 16)


def _format_srt_time(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _escape_ffmpeg_filter_path(path: str) -> str:
    """Escape a path for inline ffmpeg filter graphs (subtitles=...)."""
    return path.replace("\\", "\\\\").replace(":", "\\:").replace("'", r"\\'").replace(",", r"\\,")


async def _run_ffmpeg(cmd: list[str], timeout: float) -> None:
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    try:
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except TimeoutError as exc:
        proc.kill()
        await proc.wait()
        raise RuntimeError(f"ffmpeg timed out after {timeout}s: {' '.join(cmd)}") from exc

    if proc.returncode != 0:
        raise RuntimeError(
            f"ffmpeg failed (code {proc.returncode}): {stderr.decode(errors='replace')[:1000]}"
        )


class SceneProductionCoordinator:
    """Produce all multimedia assets for one scene at a time.

    Models are passed in (already loaded by the caller) so the caller controls
    GPU memory across the pipeline.
    """

    def __init__(
        self,
        tts_model,
        music_model,
        image_model,
        video_model,
        characters: list[Character],
        output_dir: Path | None = None,
        character_references: list[CharacterReference] | None = None,
        target_age: int = 6,
    ) -> None:
        self.tts_model = tts_model
        self.music_model = music_model
        self.image_model = image_model
        self.video_model = video_model
        self.characters = characters
        self.output_dir = output_dir or Path("output")
        self.scenes_dir = self.output_dir / "scenes"
        self.scenes_dir.mkdir(parents=True, exist_ok=True)
        self.target_age = target_age
        self._ref_lookup: dict[str, str] = {
            r.name: r.portrait_path for r in (character_references or []) if r.portrait_path
        }

    def _pick_reference(self, scene_characters: list[str]) -> str | None:
        for name in scene_characters:
            if name in self._ref_lookup:
                return self._ref_lookup[name]
        return None

    async def produce_scene(
        self,
        scene: SceneSpec,
        resume: bool = False,
        on_step_complete: Callable[[], None] | None = None,
    ) -> SceneSpec:
        """Produce all assets for a scene.

        When `resume=True`, any sub-step whose output file already exists on disk
        is skipped. `on_step_complete` is invoked after every step that actually
        produced something — use it to persist the scene manifest so mid-scene
        crashes can resume from the last completed sub-step.
        """
        logger.info(f"Producing scene {scene.id}")

        def _save() -> None:
            if on_step_complete is not None:
                on_step_complete()

        # Narration sets the master timing — must be available before the rest.
        if resume and scene.narration and Path(scene.narration.file).exists():
            narration = scene.narration
            logger.info(f"Scene {scene.id}: resuming with existing narration")
        else:
            narration = await self._generate_narration(scene)
            scene.narration = narration
            _save()

        if resume and scene.image and Path(scene.image.file).exists():
            image = scene.image
            logger.info(f"Scene {scene.id}: resuming with existing image")
        else:
            image = await self._get_or_generate_image(scene)
            scene.image = image
            _save()

        if resume and scene.video and Path(scene.video.file).exists():
            logger.info(f"Scene {scene.id}: resuming with existing video")
        else:
            video = await self._generate_video(scene, image, target_duration=narration.duration)
            scene.video = video
            _save()

        if resume and scene.music and Path(scene.music.file).exists():
            logger.info(f"Scene {scene.id}: resuming with existing music")
        else:
            music = await self._generate_music(scene, target_duration=narration.duration)
            scene.music = music
            _save()

        if resume and scene.subtitles and Path(scene.subtitles.file).exists():
            logger.info(f"Scene {scene.id}: resuming with existing subtitles")
        else:
            subtitles = await self._generate_subtitles(scene, narration)
            scene.subtitles = subtitles
            _save()

        if resume and scene.composite and Path(scene.composite).exists():
            logger.info(f"Scene {scene.id}: resuming with existing composite")
        else:
            composite = await self._composite_scene(scene)
            scene.composite = composite
            _save()

        return scene

    async def _generate_narration(self, scene: SceneSpec) -> NarrationAsset:
        out_file = self.scenes_dir / f"{scene.id}_narration.m4a"
        audio_bytes = await self.tts_model.generate_speech(text=scene.text)
        out_file.write_bytes(audio_bytes)

        actual_duration = await asyncio.to_thread(self._probe_duration, out_file)

        words = scene.text.split()
        chunk_size = max(4, min(8, len(words) // max(1, int(actual_duration / 2))))
        chunks = [" ".join(words[i : i + chunk_size]) for i in range(0, len(words), chunk_size)]

        logger.info(f"Scene {scene.id}: narration {actual_duration:.2f}s, {len(words)} words")
        return NarrationAsset(
            file=str(out_file),
            duration=actual_duration,
            text_chunks=chunks,
        )

    def _probe_duration(self, audio_file: Path) -> float:
        import mutagen

        audio = mutagen.File(str(audio_file))
        if audio is None or not hasattr(audio, "info"):
            raise RuntimeError(f"Could not probe duration of {audio_file}")
        return float(audio.info.length)

    async def _get_or_generate_image(self, scene: SceneSpec) -> ImageAsset:
        if scene.illustration_reference:
            image_file = Path(scene.illustration_reference)
            if not image_file.exists():
                raise FileNotFoundError(
                    f"Scene {scene.id} references missing book illustration: {image_file}"
                )
            width, height = await asyncio.to_thread(self._probe_image_size, image_file)
            logger.info(f"Scene {scene.id}: reusing book illustration {image_file.name}")
            return ImageAsset(file=str(image_file), source="book", width=width, height=height)

        out_file = self.scenes_dir / f"{scene.id}_image.png"
        prompt = self._build_image_prompt(scene)
        seed = _scene_seed(scene.id)
        ref_path = self._pick_reference(scene.characters)
        negative = build_negative_prompt(self.target_age)

        if ref_path:
            logger.info(f"Scene {scene.id}: generating image with ref {Path(ref_path).name}")
            img_bytes = await self.image_model.generate_with_reference(
                prompt=prompt,
                reference_image_path=ref_path,
                width=1280,
                height=720,
                seed=seed,
                negative_prompt=negative,
            )
        else:
            logger.info(f"Scene {scene.id}: generating image text-only (seed={seed})")
            img_bytes = await self.image_model.generate_image(
                prompt=prompt,
                width=1280,
                height=720,
                seed=seed,
                negative_prompt=negative,
            )
        out_file.write_bytes(img_bytes)
        return ImageAsset(file=str(out_file), source="generated", width=1280, height=720)

    def _probe_image_size(self, path: Path) -> tuple[int, int]:
        with Image.open(path) as img:
            return img.size

    def _build_image_prompt(self, scene: SceneSpec) -> str:
        return build_scene_prompt_for_movie(
            scene_text=scene.text,
            setting=scene.setting,
            mood=scene.mood,
            characters_in_scene=scene.characters,
            full_cast=self.characters,
            illustration_style=config.style.illustration_style,
        )

    async def _generate_video(
        self,
        scene: SceneSpec,
        image: ImageAsset,
        target_duration: float,
    ) -> VideoAsset:
        out_file = self.scenes_dir / f"{scene.id}_video.mp4"

        if self.video_model is None:
            await self._render_static_video(image.file, out_file, target_duration)
            logger.info(f"Scene {scene.id}: static video {target_duration:.2f}s")
        else:
            anim_prompt = self._build_video_prompt(scene)
            seed = _scene_seed(scene.id) ^ 0xA5A5A5A5
            raw_video = self.scenes_dir / f"{scene.id}_video_raw.mp4"
            await self.video_model.generate_video(
                image_path=Path(image.file),
                prompt=anim_prompt,
                output_path=raw_video,
                seed=seed,
            )
            await self._fit_video_duration(raw_video, out_file, target_duration)
            raw_video.unlink(missing_ok=True)
            logger.info(f"Scene {scene.id}: AI video → {target_duration:.2f}s")

        return VideoAsset(
            file=str(out_file), duration=target_duration, fps=config.model.video_generation.fps
        )

    def _build_video_prompt(self, scene: SceneSpec) -> str:
        return (
            f"{scene.text.strip()} "
            f"Mood: {scene.mood}. Setting: {scene.setting}. "
            f"{config.style.video_animation_style}, "
            "subtle natural motion, soft warm lighting, children's storybook animation."
        )

    async def _render_static_video(self, image_path: str, out_path: Path, duration: float) -> None:
        cmd = [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            image_path,
            "-t",
            f"{duration:.3f}",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-vf",
            "scale=1280:720:force_original_aspect_ratio=decrease,"
            "pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=black",
            "-r",
            str(config.model.video_generation.fps),
            str(out_path),
        ]
        await _run_ffmpeg(cmd, timeout=120)

    async def _fit_video_duration(
        self, input_path: Path, out_path: Path, target_duration: float
    ) -> None:
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(input_path),
            "-t",
            f"{target_duration:.3f}",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-vf",
            "scale=1280:720:force_original_aspect_ratio=decrease,"
            "pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=black",
            "-r",
            str(config.model.video_generation.fps),
            "-an",
            str(out_path),
        ]
        await _run_ffmpeg(cmd, timeout=120)

    async def _generate_music(self, scene: SceneSpec, target_duration: float) -> MusicAsset:
        out_file = self.scenes_dir / f"{scene.id}_music.mp3"
        temp_wav = self.scenes_dir / f"{scene.id}_music_raw.wav"

        prompt = (
            f"{scene.mood}, {scene.setting} atmosphere, {config.style.music_style}, instrumental"
        )
        max_new_tokens = max(256, int(target_duration * 50))
        music_bytes = await self.music_model.generate_music(prompt, max_new_tokens=max_new_tokens)
        temp_wav.write_bytes(music_bytes)

        fade_start = max(0.0, target_duration - 0.5)
        cmd = [
            "ffmpeg",
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            str(temp_wav),
            "-t",
            f"{target_duration:.3f}",
            "-af",
            f"afade=t=in:st=0:d=0.5,afade=t=out:st={fade_start:.3f}:d=0.5",
            "-c:a",
            "libmp3lame",
            "-b:a",
            "128k",
            str(out_file),
        ]
        await _run_ffmpeg(cmd, timeout=120)
        temp_wav.unlink(missing_ok=True)

        logger.info(f"Scene {scene.id}: music {target_duration:.2f}s")
        return MusicAsset(file=str(out_file), duration=target_duration, fade_in=0.5, fade_out=0.5)

    async def _generate_subtitles(
        self, scene: SceneSpec, narration: NarrationAsset
    ) -> SubtitleAsset:
        out_file = self.scenes_dir / f"{scene.id}.srt"
        chunks = narration.text_chunks or [scene.text]
        chunk_duration = narration.duration / len(chunks)

        lines: list[str] = []
        for i, chunk in enumerate(chunks, 1):
            start = (i - 1) * chunk_duration
            end = i * chunk_duration
            lines.append(str(i))
            lines.append(f"{_format_srt_time(start)} --> {_format_srt_time(end)}")
            lines.append(chunk)
            lines.append("")

        out_file.write_text("\n".join(lines), encoding="utf-8")
        return SubtitleAsset(file=str(out_file), format="SRT")

    async def _composite_scene(self, scene: SceneSpec) -> str:
        out_file = self.scenes_dir / f"{scene.id}_final.mp4"
        subtitle_path = _escape_ffmpeg_filter_path(str(Path(scene.subtitles.file).resolve()))

        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            scene.video.file,
            "-i",
            scene.narration.file,
            "-i",
            scene.music.file,
            "-filter_complex",
            "[1:a]volume=1.0[a1];[2:a]volume=0.25[a2];[a1][a2]amix=inputs=2:duration=first[audio]",
            "-vf",
            f"subtitles=filename='{subtitle_path}'",
            "-map",
            "0:v",
            "-map",
            "[audio]",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "23",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-pix_fmt",
            "yuv420p",
            "-shortest",
            str(out_file),
        ]
        await _run_ffmpeg(cmd, timeout=300)
        logger.info(f"Scene {scene.id}: composite ready")
        return str(out_file)

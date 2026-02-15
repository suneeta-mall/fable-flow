"""Image-to-video generation.

Dispatches on `config.model.video_generation.model`:
- `Wan-AI/Wan2.1-I2V-14B-720P-Diffusers` (or any `Wan-AI/*`) → WanImageToVideoPipeline
- `hunyuanvideo-community/HunyuanVideo-I2V` → HunyuanVideoImageToVideoPipeline

Wan2.1 is the default — at SOTA-tier for subtle, controllable motion suitable
for children's book scenes. HunyuanVideo is still available for users who
prefer it.
"""

from __future__ import annotations

import asyncio
import gc
from pathlib import Path

import torch
from diffusers import (
    HunyuanVideoImageToVideoPipeline,
    HunyuanVideoTransformer3DModel,
    WanImageToVideoPipeline,
)
from diffusers.utils import export_to_video
from loguru import logger
from PIL import Image

from fable_flow.config import config


class EnhancedVideoModel:
    """Image-to-video generation with model-family dispatch."""

    def __init__(self) -> None:
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.cfg = config.model.video_generation
        self.model_id = self.cfg.model

        if self._is_wan:
            self._load_wan()
        else:
            self._load_hunyuan()

    @property
    def _is_wan(self) -> bool:
        return self.model_id.lower().startswith("wan-ai/") or "wan" in self.model_id.lower()[:8]

    def _load_wan(self) -> None:
        logger.info(f"Loading Wan video model: {self.model_id}")
        self.pipeline = WanImageToVideoPipeline.from_pretrained(
            self.model_id,
            torch_dtype=torch.bfloat16,
        )
        # Wan I2V (14B) doesn't fit fully on a single A100. Use the
        # diffusers-provided offload — and do NOT also call .to(device), or
        # the entire model gets moved to GPU first and OOMs.
        if self.device == "cuda" and hasattr(self.pipeline, "enable_model_cpu_offload"):
            self.pipeline.enable_model_cpu_offload()

    def _load_hunyuan(self) -> None:
        logger.info(f"Loading HunyuanVideo model: {self.model_id}")
        transformer = HunyuanVideoTransformer3DModel.from_pretrained(
            self.model_id, subfolder="transformer", torch_dtype=torch.bfloat16
        )
        self.pipeline = HunyuanVideoImageToVideoPipeline.from_pretrained(
            self.model_id, transformer=transformer, torch_dtype=torch.float16
        )
        self.pipeline.vae.enable_tiling()
        # HunyuanVideo also doesn't fit fully — use model CPU offload, no .to().
        if self.device == "cuda" and hasattr(self.pipeline, "enable_model_cpu_offload"):
            self.pipeline.enable_model_cpu_offload()

    async def generate_video(
        self,
        image_path: Path,
        prompt: str,
        output_path: Path,
        seed: int | None = None,
    ) -> Path:
        return await asyncio.to_thread(self._generate_sync, image_path, prompt, output_path, seed)

    def _generate_sync(
        self,
        image_path: Path,
        prompt: str,
        output_path: Path,
        seed: int | None,
    ) -> Path:
        image = Image.open(image_path).convert("RGB")
        target_w, target_h = self._fit_to_pipeline_grid(image.size)
        image = image.resize((target_w, target_h), Image.Resampling.LANCZOS)

        generator = torch.Generator(device="cpu")
        if seed is not None:
            generator.manual_seed(seed)

        if self._is_wan:
            frames = self._generate_wan(image, prompt, target_w, target_h, generator)
        else:
            frames = self._generate_hunyuan(image, prompt, target_w, target_h, generator)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        export_to_video(frames, str(output_path), fps=self.cfg.fps)

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        return output_path

    def _generate_wan(self, image, prompt, w, h, generator):
        # Wan2.1 I2V default: 81 frames @ 16fps = ~5s, similar to HunyuanVideo budget.
        num_frames = self.cfg.num_frames if self.cfg.num_frames > 0 else 81
        return self.pipeline(
            image=image,
            prompt=prompt,
            negative_prompt=self.cfg.negative_prompt,
            height=h,
            width=w,
            num_frames=num_frames,
            num_inference_steps=self.cfg.num_inference_steps,
            guidance_scale=5.0,  # Wan default; 1.0 (HunyuanVideo) is too low.
            generator=generator,
        ).frames[0]

    def _generate_hunyuan(self, image, prompt, w, h, generator):
        return self.pipeline(
            image=image,
            prompt=prompt,
            negative_prompt=self.cfg.negative_prompt,
            height=h,
            width=w,
            num_frames=self.cfg.num_frames,
            num_inference_steps=self.cfg.num_inference_steps,
            guidance_scale=self.cfg.guidance_scale,
            true_cfg_scale=self.cfg.true_cfg_scale,
            generator=generator,
        ).frames[0]

    def _fit_to_pipeline_grid(self, size: tuple[int, int]) -> tuple[int, int]:
        """Both Wan and HunyuanVideo require dimensions divisible by 16."""
        orig_w, orig_h = size
        max_w, max_h = self.cfg.width, self.cfg.height
        aspect = orig_w / orig_h
        target_aspect = max_w / max_h

        if aspect > target_aspect:
            new_w = max_w
            new_h = int(max_w / aspect)
        else:
            new_h = max_h
            new_w = int(max_h * aspect)

        new_w = max(round(new_w / 16) * 16, 512)
        new_h = max(round(new_h / 16) * 16, 512)
        return new_w, new_h

    def release(self) -> None:
        if self.pipeline is not None:
            del self.pipeline
            self.pipeline = None
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        logger.info("Released video model")

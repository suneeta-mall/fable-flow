"""Image generation with character-reference conditioning.

Dispatches on `config.model.image_generation.model`:
- `black-forest-labs/FLUX.2-*`   → Flux2Pipeline, **native `image=` conditioning** (preferred)
- `black-forest-labs/FLUX.1-*`   → FluxPipeline + XLabs IP-Adapter (legacy)
- `stabilityai/stable-diffusion-3.5-*` / `stabilityai/stable-diffusion-3-*` → SD3 (no ref conditioning)
- anything else (SDXL family)    → SDXL + h94 IP-Adapter

When `generate_with_reference(...)` is called with a character portrait, the
reference is fed in as visual conditioning — natively on FLUX 2, via IP-Adapter
on FLUX 1 / SDXL. This is how character identity stays consistent across every
illustration in a book.
"""

from __future__ import annotations

import asyncio
import gc
import io

import torch
from diffusers import (
    DPMSolverMultistepScheduler,
    Flux2Pipeline,
    FluxPipeline,
    StableDiffusion3Pipeline,
    StableDiffusionXLPipeline,
)
from loguru import logger
from PIL import Image

from fable_flow.config import config

# FLUX 1 IP-Adapter (only used when the user pins to FLUX.1-*).
_FLUX1_IP_ADAPTER_REPO = "XLabs-AI/flux-ip-adapter-v2"
_FLUX1_IP_ADAPTER_WEIGHTS = "ip_adapter.safetensors"
_FLUX1_IP_ADAPTER_IMAGE_ENCODER = "openai/clip-vit-large-patch14"

# SDXL IP-Adapter (only used when the user pins to an SDXL model).
_SDXL_IP_ADAPTER_REPO = "h94/IP-Adapter"
_SDXL_IP_ADAPTER_SUBFOLDER = "sdxl_models"
_SDXL_IP_ADAPTER_WEIGHTS = "ip-adapter-plus_sdxl_vit-h.safetensors"


class EnhancedImageModel:
    """Image generation with model-family dispatch and character-ref conditioning."""

    def __init__(self) -> None:
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_name = config.model.image_generation.model
        self.pipeline = None
        self._ip_adapter_loaded = False
        self._ip_adapter_attempted = False
        self._load_pipeline()

    @property
    def _is_flux2(self) -> bool:
        return "flux.2" in self.model_name.lower() or "flux2" in self.model_name.lower()

    @property
    def _is_flux1(self) -> bool:
        name = self.model_name.lower()
        return ("flux" in name) and not self._is_flux2

    @property
    def _is_sd3(self) -> bool:
        return "stable-diffusion-3" in self.model_name.lower()

    def _load_pipeline(self) -> None:
        logger.info(f"Loading image model: {self.model_name}")
        # Load on CPU first; placement on GPU happens via _place_on_device below.
        if self._is_flux2:
            self.pipeline = Flux2Pipeline.from_pretrained(
                self.model_name,
                torch_dtype=torch.bfloat16 if self.device == "cuda" else torch.float32,
                use_safetensors=True,
            )
        elif self._is_flux1:
            self.pipeline = FluxPipeline.from_pretrained(
                self.model_name,
                torch_dtype=torch.bfloat16 if self.device == "cuda" else torch.float32,
                use_safetensors=True,
            )
        elif self._is_sd3:
            self.pipeline = StableDiffusion3Pipeline.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                use_safetensors=True,
            )
        else:
            self.pipeline = StableDiffusionXLPipeline.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                use_safetensors=True,
            )
            self.pipeline.scheduler = DPMSolverMultistepScheduler.from_config(
                self.pipeline.scheduler.config,
                use_karras_sigmas=True,
                algorithm_type="dpmsolver++",
            )

        self._place_on_device()

        # xformers is SDXL-only and orthogonal to the offload strategy.
        if (
            self.device == "cuda"
            and not self._is_flux1
            and not self._is_flux2
            and not self._is_sd3
            and hasattr(self.pipeline, "enable_xformers_memory_efficient_attention")
        ):
            try:
                self.pipeline.enable_xformers_memory_efficient_attention()
            except Exception as e:
                logger.warning(f"xformers attention unavailable: {e}")

    def _place_on_device(self) -> None:
        """Apply the configured GPU memory strategy.

        `enable_*_cpu_offload` manages GPU placement itself — we must NOT call
        `pipeline.to(device)` alongside it, or the whole model gets shoved to
        GPU first (OOMing on large pipelines like FLUX.2-dev).
        """
        if self.device != "cuda":
            return

        strategy = (config.model.image_generation.cpu_offload or "model").lower()
        if strategy == "none":
            logger.info("Image model: full GPU placement (no offload)")
            self.pipeline = self.pipeline.to(self.device)
            return
        if strategy == "sequential":
            logger.info("Image model: sequential CPU offload (smallest VRAM, slower)")
            self.pipeline.enable_sequential_cpu_offload()
            return
        if strategy != "model":
            logger.warning(f"Unknown cpu_offload '{strategy}', falling back to 'model'")
        logger.info("Image model: model CPU offload (one submodel on GPU at a time)")
        self.pipeline.enable_model_cpu_offload()

    def _ensure_ip_adapter(self) -> bool:
        """Lazy-load IP-Adapter weights. Only used for FLUX 1 / SDXL.

        FLUX 2 doesn't need this — image conditioning is native. SD3 has no
        stable IP-Adapter yet, so we fall back to text-only.
        """
        if self._is_flux2:
            return False  # native path — don't load IP-Adapter
        if self._is_sd3:
            return False  # no stable SD3 IP-Adapter
        if self._ip_adapter_loaded:
            return True
        if self._ip_adapter_attempted:
            return False
        self._ip_adapter_attempted = True

        try:
            if self._is_flux1:
                # XLabs flux-ip-adapter-v2 wants a plain CLIPVisionModel — not
                # the projection variant that AutoModel.from_pretrained gives
                # you by default. Load the encoder explicitly to avoid:
                #   "Expected types for image_encoder: (CLIPVisionModel,),
                #    got CLIPVisionModelWithProjection."
                from transformers import CLIPVisionModel

                image_encoder = CLIPVisionModel.from_pretrained(
                    _FLUX1_IP_ADAPTER_IMAGE_ENCODER,
                    torch_dtype=torch.bfloat16 if self.device == "cuda" else torch.float32,
                )
                self.pipeline.load_ip_adapter(
                    _FLUX1_IP_ADAPTER_REPO,
                    weight_name=_FLUX1_IP_ADAPTER_WEIGHTS,
                    image_encoder=image_encoder,
                )
                self.pipeline.set_ip_adapter_scale(0.85)
            else:
                self.pipeline.load_ip_adapter(
                    _SDXL_IP_ADAPTER_REPO,
                    subfolder=_SDXL_IP_ADAPTER_SUBFOLDER,
                    weight_name=_SDXL_IP_ADAPTER_WEIGHTS,
                )
                self.pipeline.set_ip_adapter_scale(0.7)
            self._ip_adapter_loaded = True
            logger.info("IP-Adapter loaded for character-reference conditioning")
            return True
        except Exception as e:
            logger.warning(
                f"IP-Adapter unavailable for {self.model_name} ({e}); "
                "falling back to text-only generation"
            )
            return False

    async def generate_image(
        self,
        prompt: str,
        width: int = 1024,
        height: int = 1024,
        seed: int | None = None,
        negative_prompt: str | None = None,
    ) -> bytes:
        if self.pipeline is None:
            raise RuntimeError("Image pipeline not loaded")
        return await asyncio.to_thread(
            self._generate_sync, prompt, width, height, seed, negative_prompt, None
        )

    async def generate_with_reference(
        self,
        prompt: str,
        reference_image_path: str,
        width: int = 1024,
        height: int = 1024,
        seed: int | None = None,
        negative_prompt: str | None = None,
    ) -> bytes:
        """Generate conditioned on a reference image.

        - FLUX 2: native `image=` parameter (preferred path).
        - FLUX 1 / SDXL: IP-Adapter `ip_adapter_image=` parameter.
        - SD3: falls back to text-only (no stable IP-Adapter yet).
        """
        if self.pipeline is None:
            raise RuntimeError("Image pipeline not loaded")
        ref = await asyncio.to_thread(self._load_reference, reference_image_path)
        return await asyncio.to_thread(
            self._generate_sync, prompt, width, height, seed, negative_prompt, ref
        )

    def _load_reference(self, path: str) -> Image.Image:
        return Image.open(path).convert("RGB")

    def _generate_sync(
        self,
        prompt: str,
        width: int,
        height: int,
        seed: int | None,
        negative_prompt: str | None,
        reference: Image.Image | None,
    ) -> bytes:
        generator = None
        if seed is not None:
            generator = torch.Generator(device=self.device).manual_seed(seed)

        kwargs: dict = {
            "prompt": prompt,
            "height": height,
            "width": width,
            "generator": generator,
        }

        if self._is_flux2:
            # FLUX 2: image conditioning is native — pass the reference directly.
            if reference is not None:
                kwargs["image"] = reference
            kwargs["num_inference_steps"] = 50
            kwargs["guidance_scale"] = 4.0
            # FLUX 2 has no negative prompt; rely on positive prompt + identity anchor.
        elif self._is_flux1:
            if reference is not None and self._ensure_ip_adapter():
                kwargs["ip_adapter_image"] = reference
            kwargs["num_inference_steps"] = 4 if "schnell" in self.model_name.lower() else 28
            kwargs["guidance_scale"] = 3.5
            # FLUX 1 has no negative prompt either.
        else:
            # SDXL / SD3 path.
            if reference is not None and self._ensure_ip_adapter():
                kwargs["ip_adapter_image"] = reference
            kwargs["num_inference_steps"] = 30
            kwargs["guidance_scale"] = 7.5
            if negative_prompt:
                kwargs["negative_prompt"] = negative_prompt

        image = self.pipeline(**kwargs).images[0]

        buf = io.BytesIO()
        image.convert("RGB").save(buf, format="PNG")
        return buf.getvalue()

    def release(self) -> None:
        """Free GPU memory. Call before loading another large model."""
        if self.pipeline is not None:
            del self.pipeline
            self.pipeline = None
        self._ip_adapter_loaded = False
        self._ip_adapter_attempted = False
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        logger.info("Released image model")

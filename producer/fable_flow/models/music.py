from __future__ import annotations

import asyncio
import gc
import io

import soundfile as sf
import torch
from loguru import logger
from transformers import AutoProcessor, MusicgenForConditionalGeneration

from fable_flow.config import config


class EnhancedMusicModel:
    """MusicGen-small for short instrumental cues."""

    SAMPLE_RATE = 32000

    def __init__(self) -> None:
        model_id = config.model.music_generation.model
        logger.info(f"Loading music model: {model_id}")
        self.processor = AutoProcessor.from_pretrained(model_id)
        self.model = MusicgenForConditionalGeneration.from_pretrained(model_id)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        if self.device == "cuda":
            self.model = self.model.to(self.device)

    async def generate_music(self, prompt: str, max_new_tokens: int = 256) -> bytes:
        return await asyncio.to_thread(self._generate_sync, prompt, max_new_tokens)

    def _generate_sync(self, prompt: str, max_new_tokens: int) -> bytes:
        inputs = self.processor(text=[prompt], padding=True, return_tensors="pt")
        if self.device == "cuda":
            inputs = inputs.to(self.device)

        audio_values = self.model.generate(**inputs, max_new_tokens=max_new_tokens)
        audio_np = audio_values[0].cpu().numpy()

        buf = io.BytesIO()
        sf.write(buf, audio_np.T, self.SAMPLE_RATE, format="WAV")
        return buf.getvalue()

    def release(self) -> None:
        del self.model
        del self.processor
        self.model = None
        self.processor = None
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        logger.info("Released music model")

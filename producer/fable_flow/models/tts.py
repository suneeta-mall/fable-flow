from __future__ import annotations

import asyncio
import io
import os
import re
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from kokoro import KPipeline
from loguru import logger
from pydub import AudioSegment

from fable_flow.config import config


class EnhancedTTSModel:
    """Kokoro TTS with sentence-aware chunking for long passages."""

    def __init__(self) -> None:
        self.voice_preset = config.model.text_to_speech.voice_preset
        self.sample_rate = config.model.text_to_speech.sample_rate
        self.pipeline = KPipeline(lang_code=config.model.text_to_speech.lang_code)

    async def generate_speech(self, text: str, voice_id: str | None = None) -> bytes:
        prepared = self._prepare_text(text)
        voice = voice_id or self.voice_preset
        return await asyncio.to_thread(self._generate_sync, prepared, voice)

    def _prepare_text(self, text: str) -> str:
        if not text or not text.strip():
            raise ValueError("Cannot synthesize empty text")
        text = re.sub(r"[^\w\s.,!?;:\-']", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _chunk_text(self, text: str, max_chunk_size: int = 500) -> list[str]:
        if len(text) <= max_chunk_size:
            return [text]

        chunks: list[str] = []
        remaining = text
        while remaining:
            if len(remaining) <= max_chunk_size:
                chunks.append(remaining)
                break

            chunk_end = max_chunk_size
            for punct in [". ", "! ", "? "]:
                pos = remaining.rfind(punct, max_chunk_size // 2, max_chunk_size)
                if pos != -1:
                    chunk_end = pos + len(punct.strip())
                    break
            if chunk_end == max_chunk_size:
                pos = remaining.rfind("\n\n", max_chunk_size // 2, max_chunk_size)
                if pos != -1:
                    chunk_end = pos + 2
            if chunk_end == max_chunk_size:
                for punct in [", ", "; "]:
                    pos = remaining.rfind(punct, max_chunk_size // 2, max_chunk_size)
                    if pos != -1:
                        chunk_end = pos + len(punct.strip())
                        break

            chunks.append(remaining[:chunk_end].strip())
            remaining = remaining[chunk_end:].strip()

        return chunks

    def _generate_sync(self, text: str, voice: str) -> bytes:
        chunks = self._chunk_text(text)
        segments: list[np.ndarray] = []

        for i, chunk in enumerate(chunks):
            audio_np = self._synth_chunk(chunk, voice)
            segments.append(audio_np)
            if i < len(chunks) - 1:
                segments.append(np.zeros(int(0.3 * self.sample_rate), dtype=np.float32))

        if not segments:
            raise RuntimeError("TTS produced no audio")

        merged = np.concatenate(segments)
        return self._encode_m4a(merged)

    def _synth_chunk(self, text: str, voice: str) -> np.ndarray:
        for _gs, _ps, audio in self.pipeline(text, voice=voice):
            if isinstance(audio, torch.Tensor):
                audio_np = audio.cpu().numpy()
            elif isinstance(audio, np.ndarray):
                audio_np = audio
            else:
                audio_np = np.array(audio, dtype=np.float32)

            if audio_np.dtype != np.float32:
                audio_np = audio_np.astype(np.float32)
            peak = np.abs(audio_np).max()
            if peak > 1.0:
                audio_np = audio_np / peak
            return audio_np

        raise RuntimeError(f"TTS yielded nothing for: {text[:80]!r}")

    def _encode_m4a(self, audio_data: np.ndarray) -> bytes:
        wav_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as wav_file:
                wav_path = Path(wav_file.name)
            sf.write(str(wav_path), audio_data, self.sample_rate)
            seg = AudioSegment.from_wav(str(wav_path))
            out = io.BytesIO()
            seg.export(out, format="mp4", codec="aac", bitrate="128k")
            return out.getvalue()
        finally:
            if wav_path and wav_path.exists():
                os.unlink(wav_path)

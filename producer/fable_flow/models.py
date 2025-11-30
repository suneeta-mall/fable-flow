import io
import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Union, overload

import numpy as np
import openai
import soundfile as sf
import torch
from diffusers import (
    DPMSolverMultistepScheduler,
    FluxPipeline,
    HunyuanVideoImageToVideoPipeline,
    HunyuanVideoTransformer3DModel,
    StableDiffusion3Pipeline,
    StableDiffusionPipeline,
    StableDiffusionXLPipeline,
)
from diffusers.utils import load_image
from kokoro import KPipeline
from moviepy import ImageSequenceClip
from PIL import Image
from pydub import AudioSegment
from transformers import (
    AutoProcessor,
    MusicgenForConditionalGeneration,
)

from .config import config
from .continuation import ContinuationService

logger = logging.getLogger(__name__)


class EnhancedTextModel:
    """Enhanced text model with robust continuation support."""

    def __init__(self, model_name: str = config.model.default) -> None:
        self.model_name = model_name
        self.client = openai.AsyncClient(
            api_key=config.model.server.api_key,
            base_url=config.model.server.url,
            timeout=config.model.server.timeout,
            max_retries=config.model.server.max_retries,
        )
        # Initialize continuation service
        self.continuation_service = ContinuationService(self.client, self.model_name)

    async def generate(self, prompt: str, system_message: str) -> str:
        """Generate text using robust continuation service."""
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt},
        ]

        content, metadata = await self.continuation_service.generate_with_continuation(messages)

        # Log metadata for debugging
        logger.info(f"Generation completed: {metadata}")

        return content


class EnhancedImageModel:
    def __init__(self) -> None:
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_name = config.model.image_generation.model
        self.pipeline: FluxPipeline | StableDiffusion3Pipeline | StableDiffusionPipeline | None = (
            None
        )
        self._load_pipeline()

    def _load_pipeline(self) -> None:
        """Load the appropriate diffusion pipeline based on model configuration."""
        if "flux" in self.model_name.lower():
            # FLUX.1 models - need special handling
            self.pipeline = FluxPipeline.from_pretrained(
                self.model_name,
                torch_dtype=torch.bfloat16 if self.device == "cuda" else torch.float32,
                use_safetensors=True,
            )
            # FLUX models don't work well with xformers, so we skip that
            if self.device == "cuda" and self.pipeline is not None:
                self.pipeline = self.pipeline.to(self.device)
                # Only enable CPU offload for FLUX, not xformers
                self.pipeline.enable_model_cpu_offload()

        elif "stable-diffusion-3" in self.model_name.lower():
            # Stable Diffusion 3 models
            self.pipeline = StableDiffusion3Pipeline.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                use_safetensors=True,
            )
            if self.device == "cuda":
                self.pipeline = self.pipeline.to(self.device)
                self.pipeline.enable_model_cpu_offload()

        else:
            # Default to Stable Diffusion XL
            self.pipeline = StableDiffusionXLPipeline.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                use_safetensors=True,
            )
            # Use DPM++ 2M Karras scheduler for better quality
            if self.pipeline is not None:
                self.pipeline.scheduler = DPMSolverMultistepScheduler.from_config(
                    self.pipeline.scheduler.config,
                    use_karras_sigmas=True,
                    algorithm_type="dpmsolver++",
                )
                if self.device == "cuda":
                    self.pipeline = self.pipeline.to(self.device)
                    self.pipeline.enable_model_cpu_offload()
                    # Only enable xformers for SDXL, not FLUX
                    if hasattr(self.pipeline, "enable_xformers_memory_efficient_attention"):
                        try:
                            self.pipeline.enable_xformers_memory_efficient_attention()
                        except Exception:
                            print(
                                "Warning: Could not enable xformers attention, continuing without it"
                            )

    async def generate_image(
        self, prompt: str, style: dict[str, str], width: int = 1024, height: int = 1024
    ) -> bytes:
        if self.pipeline is None:
            raise RuntimeError("Pipeline not loaded. Call _load_pipeline() first.")

        # Construct the full prompt with style information
        default_style_preset = "children's book illustration"
        style_prompt = f"{prompt}. Style: {style.get('style_preset', default_style_preset)}, {style.get('color_scheme', 'bright and cheerful')}, {style.get('art_style', 'watercolor and digital art blend')}"

        # Different parameters for different model types
        if "flux" in self.model_name.lower():
            # FLUX models have different parameter requirements
            image = self.pipeline(
                prompt=style_prompt,
                height=height,
                width=width,
                num_inference_steps=4
                if "schnell" in self.model_name.lower()
                else 20,  # Schnell is designed for fewer steps
                guidance_scale=3.5,  # FLUX works better with lower guidance
                generator=torch.Generator(device=self.device).manual_seed(42),
            ).images[0]
        else:
            # SDXL and SD3 models
            image = self.pipeline(
                prompt=style_prompt,
                height=height,
                width=width,
                num_inference_steps=30,  # Good balance of quality and speed
                guidance_scale=7.5,  # Good prompt adherence
                generator=torch.Generator(device=self.device).manual_seed(42),
            ).images[0]

        # Convert PIL Image to bytes
        img_buffer = io.BytesIO()
        image.save(img_buffer, format="PNG", optimize=True)
        return img_buffer.getvalue()


class EnhancedMusicModel:
    def __init__(self) -> None:
        self.processor = AutoProcessor.from_pretrained("facebook/musicgen-small")
        self.model = MusicgenForConditionalGeneration.from_pretrained("facebook/musicgen-small")
        if torch.cuda.is_available():
            self.model = self.model.to("cuda")

    async def generate_music(self, mood: str) -> bytes:
        style = config.style.music.get(mood, config.style.music["happy"])
        inputs = self.processor(
            text=[style],
            padding=True,
            return_tensors="pt",
        )
        if torch.cuda.is_available():
            inputs = inputs.to("cuda")

        audio_values = self.model.generate(**inputs, max_new_tokens=256)
        audio_data = io.BytesIO()
        audio_numpy = audio_values[0].cpu().numpy()
        sf.write(audio_data, audio_numpy.T, 32000, format="WAV")
        return audio_data.getvalue()


class EnhancedTTSModel:
    def __init__(self) -> None:
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.voice_preset = config.model.text_to_speech.voice_preset
        self.sample_rate = config.model.text_to_speech.sample_rate
        self.pipeline = KPipeline(lang_code="a")  # 'a' for American English

    def _prepare_text(self, text: str) -> str:
        """Clean and normalize text for TTS generation."""
        if not text or not text.strip():
            return "Hi."

        # Clean and normalize text
        text = re.sub(r"[^\w\s.,!?;:\-']", " ", text)
        text = re.sub(r"\s+", " ", text).strip()

        return text

    def _chunk_text(self, text: str, max_chunk_size: int = 500) -> list[str]:
        """
        Split text into chunks for batch processing.
        Tries to break at sentence boundaries to maintain natural flow.
        """
        if len(text) <= max_chunk_size:
            return [text]

        chunks = []
        remaining_text = text

        while remaining_text:
            if len(remaining_text) <= max_chunk_size:
                chunks.append(remaining_text)
                break

            # Try to find a good breaking point near the max chunk size
            chunk_end = max_chunk_size

            # Look for sentence endings (. ! ?) within reasonable distance
            for punct in [". ", "! ", "? "]:
                punct_pos = remaining_text.rfind(punct, max_chunk_size // 2, max_chunk_size)
                if punct_pos != -1:
                    chunk_end = punct_pos + len(punct.strip())
                    break

            # If no sentence break found, try paragraph breaks
            if chunk_end == max_chunk_size:
                para_pos = remaining_text.rfind("\n\n", max_chunk_size // 2, max_chunk_size)
                if para_pos != -1:
                    chunk_end = para_pos + 2

            # If no good break found, try comma or semicolon
            if chunk_end == max_chunk_size:
                for punct in [", ", "; "]:
                    punct_pos = remaining_text.rfind(punct, max_chunk_size // 2, max_chunk_size)
                    if punct_pos != -1:
                        chunk_end = punct_pos + len(punct.strip())
                        break

            # Extract the chunk
            chunk = remaining_text[:chunk_end].strip()
            if chunk:
                chunks.append(chunk)

            # Move to the next chunk
            remaining_text = remaining_text[chunk_end:].strip()

        return chunks

    def get_audio_format_info(self) -> dict[str, str]:
        """Get information about the audio format being generated."""
        return {"format": "m4a", "extension": ".m4a", "mime_type": "audio/mp4"}

    async def generate_speech(self, text: str, voice_id: str = "default") -> bytes:
        """Generate speech using Kokoro-TTS with chunking for long text."""
        prepared_text = self._prepare_text(text)
        voice = voice_id if voice_id != "default" else self.voice_preset

        # Split text into manageable chunks
        text_chunks = self._chunk_text(prepared_text, max_chunk_size=500)

        if len(text_chunks) == 1:
            # Single chunk - process normally
            return await self._generate_single_chunk(text_chunks[0], voice)
        else:
            # Multiple chunks - process in batches and concatenate
            return await self._generate_multiple_chunks(text_chunks, voice)

    @overload
    async def _generate_single_chunk(
        self, text: str, voice: str, return_raw: bool = False
    ) -> bytes: ...

    @overload
    async def _generate_single_chunk(
        self, text: str, voice: str, return_raw: bool = True
    ) -> np.ndarray: ...

    async def _generate_single_chunk(
        self, text: str, voice: str, return_raw: bool = False
    ) -> bytes | np.ndarray:
        """Generate speech for a single text chunk."""
        generator = self.pipeline(text, voice=voice)

        # Get the first (and usually only) generated audio
        for _i, (_gs, _ps, audio) in enumerate(generator):
            # Ensure audio is the right type
            if isinstance(audio, torch.Tensor):
                audio_np = audio.cpu().numpy()
            elif isinstance(audio, np.ndarray):
                audio_np = audio
            else:
                # Convert other types to numpy
                audio_np = np.array(audio, dtype=np.float32)

            if return_raw:
                # Return raw numpy array for concatenation
                if audio_np.dtype != np.float32:
                    audio_np = audio_np.astype(np.float32)
                # Normalize if needed
                if np.abs(audio_np).max() > 1.0:
                    audio_np = audio_np / np.abs(audio_np).max()
                return audio_np
            else:
                # Return converted bytes (M4A format)
                return self._audio_to_bytes(audio_np, self.sample_rate, "m4a")

        # No audio generated - this should not happen with proper models
        raise RuntimeError(f"No audio generated for text: {text[:50]}...")

    async def _generate_multiple_chunks(self, text_chunks: list[str], voice: str) -> bytes:
        """Generate speech for multiple text chunks and concatenate them."""
        audio_segments = []

        print(f"🔊 Generating speech for {len(text_chunks)} chunks...")

        for i, chunk in enumerate(text_chunks):
            print(f"   Processing chunk {i + 1}/{len(text_chunks)}: {chunk[:50]}...")

            # Generate raw audio data for this chunk (not converted to M4A yet)
            chunk_audio_data = await self._generate_single_chunk(chunk, voice, return_raw=True)
            audio_segments.append(chunk_audio_data)

            # Add a small pause between chunks (0.3 seconds)
            if i < len(text_chunks) - 1:
                pause = np.zeros(int(0.3 * self.sample_rate), dtype=np.float32)
                audio_segments.append(pause)

        if not audio_segments:
            raise RuntimeError("No audio segments were generated - all chunks failed")

        # Concatenate all audio segments
        concatenated_audio = np.concatenate(audio_segments)
        print(
            f"✅ Successfully concatenated {len(text_chunks)} chunks into {len(concatenated_audio) / self.sample_rate:.1f} seconds of audio"
        )
        return self._audio_to_bytes(concatenated_audio, self.sample_rate, "m4a")

    def _audio_to_bytes(
        self, audio_data: np.ndarray | torch.Tensor, sample_rate: int, format: str = "m4a"
    ) -> bytes:
        """Convert audio data to bytes using pydub for format conversion."""
        wav_path = None
        try:
            # Create temporary WAV file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as wav_file:
                wav_path = Path(wav_file.name)

            # Convert to numpy if needed
            if isinstance(audio_data, torch.Tensor):
                audio_data = audio_data.cpu().numpy()

            # Ensure audio is in correct format
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)

            # Normalize if needed
            if np.abs(audio_data).max() > 1.0:
                audio_data = audio_data / np.abs(audio_data).max()

            # Write to WAV first
            sf.write(str(wav_path), audio_data, sample_rate)

            audio_segment = AudioSegment.from_wav(str(wav_path))

            # Export to desired format in memory
            output_buffer = io.BytesIO()

            if format.lower() == "m4a":
                # Export as M4A with good compression settings
                audio_segment.export(
                    output_buffer,
                    format="mp4",  # pydub uses 'mp4' for m4a files
                    codec="aac",
                    bitrate="128k",
                )
            elif format.lower() == "mp3":
                # Export as MP3
                audio_segment.export(output_buffer, format="mp3", bitrate="128k")
            else:
                # Default to WAV (uncompressed)
                audio_segment.export(output_buffer, format="wav")

            return output_buffer.getvalue()

        finally:
            # Always clean up temp files
            if wav_path and wav_path.exists():
                os.unlink(wav_path)


class EnhancedVideoModel:
    def __init__(self) -> None:
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32
        self.use_cpu_offload = False

        # Load HunyuanVideo-I2V model
        model_id = config.model.video_generation.get(
            "model", "hunyuanvideo-community/HunyuanVideo-I2V"
        )

        logger.info(f"Loading HunyuanVideo-I2V model: {model_id}...")
        logger.info(f"Using device: {self.device}, dtype: {self.dtype}")

        # Set default device to CUDA to ensure all tensors are created on GPU
        # This helps avoid device mismatch issues with the text encoder
        if torch.cuda.is_available():
            torch.set_default_device("cuda")
            logger.info("Set default device to CUDA")

        # Load the transformer separately with bfloat16 (recommended approach)
        logger.info("Loading HunyuanVideoTransformer3DModel...")
        transformer = HunyuanVideoTransformer3DModel.from_pretrained(
            model_id, subfolder="transformer", torch_dtype=torch.bfloat16
        )

        # Load the HunyuanVideo Image-to-Video pipeline with the transformer
        logger.info("Loading HunyuanVideoImageToVideoPipeline...")
        self.model = HunyuanVideoImageToVideoPipeline.from_pretrained(
            model_id,
            transformer=transformer,
            torch_dtype=torch.float16,
        )

        # Reset default device to avoid affecting other code
        if torch.cuda.is_available():
            torch.set_default_device("cpu")
            logger.info("Reset default device to CPU")

        # Enable VAE tiling to save memory
        logger.info("Enabling VAE tiling for memory optimization...")
        self.model.vae.enable_tiling()

        if torch.cuda.is_available():
            logger.info("Moving HunyuanVideo model components to CUDA...")
            # Explicitly move each component to CUDA to avoid device mismatch
            # The text encoder in particular needs explicit device placement
            if hasattr(self.model, "text_encoder") and self.model.text_encoder is not None:
                self.model.text_encoder = self.model.text_encoder.to(self.device)
                logger.info("Text encoder moved to CUDA")

            if hasattr(self.model, "transformer") and self.model.transformer is not None:
                self.model.transformer = self.model.transformer.to(self.device)
                logger.info("Transformer moved to CUDA")

            if hasattr(self.model, "vae") and self.model.vae is not None:
                self.model.vae = self.model.vae.to(self.device)
                logger.info("VAE moved to CUDA")

            # Move the entire pipeline as well
            self.model = self.model.to(self.device)
            self.use_cpu_offload = False
            logger.info("All model components moved to CUDA successfully")

        logger.info("HunyuanVideo-I2V model loaded successfully!")

    async def generate_video(self, story: str, style: dict[str, str], output_dir: Path) -> list:
        """Generate video using HunyuanVideo-I2V model with image-to-video generation."""
        scene_prompts = re.findall(r"<storyboard>(.*?)</storyboard>", story, re.DOTALL)
        clip_sequence = []
        video_config = config.model.video_generation

        for i, prompt in enumerate(scene_prompts):
            logger.info(
                f"Generating video for scene {i + 1}/{len(scene_prompts)} with HunyuanVideo-I2V..."
            )

            # Load the corresponding image generated by the illustrator
            image_path = output_dir / f"image_{i}.png"
            if not image_path.exists():
                logger.warning(f"Image not found: {image_path}, skipping scene {i + 1}")
                continue

            image = load_image(str(image_path))
            logger.info(f"Loaded image from {image_path} with size: {image.size}")

            # Build style-enhanced prompt
            style_prompt = f"Style: {style.get('animation_style', '3D animation')}, {style.get('color_palette', 'vibrant')}, {style.get('camera_style', 'dynamic')}"

            sentences = prompt.split(".")
            concise_prompt = ". ".join(sentences[:3]) + ". " + style_prompt

            # HunyuanVideo-I2V supports up to 720p (1280x720) and up to 129 frames (5 seconds)
            # Default resolution settings from config
            target_height = video_config.get("height", 720)
            target_width = video_config.get("width", 1280)

            # Resize image to target resolution while maintaining aspect ratio
            original_width, original_height = image.size
            aspect_ratio = original_width / original_height

            if aspect_ratio > (target_width / target_height):
                # Image is wider, fit to width
                new_width = target_width
                new_height = int(target_width / aspect_ratio)
            else:
                # Image is taller, fit to height
                new_height = target_height
                new_width = int(target_height * aspect_ratio)

            # Ensure dimensions are reasonable for HunyuanVideo
            new_width = max(min(new_width, target_width), 512)
            new_height = max(min(new_height, target_height), 512)

            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            logger.info(f"Resized image to {new_width}x{new_height} for HunyuanVideo processing")

            # Generate video using HunyuanVideo-I2V pipeline
            # Always use CPU for generator to avoid device mismatch issues
            generator = torch.Generator(device="cpu").manual_seed(42)
            logger.info("Using CPU generator to avoid device mismatch")

            # Set default device to CUDA during inference to ensure all tensors
            # created by the text encoder are on the correct device
            if torch.cuda.is_available():
                torch.set_default_device("cuda")

            try:
                video_frames = self.model(
                    image=image,
                    prompt=concise_prompt,
                    negative_prompt=video_config.get("negative_prompt", ""),
                    height=new_height,
                    width=new_width,
                    num_frames=video_config.get("num_frames", 129),
                    num_inference_steps=video_config.get("num_inference_steps", 50),
                    guidance_scale=video_config.get("guidance_scale", 1.0),
                    true_cfg_scale=video_config.get(
                        "true_cfg_scale", 6.0
                    ),  # HunyuanVideo uses dual guidance
                    generator=generator,
                ).frames[0]
            finally:
                # Reset default device after inference
                if torch.cuda.is_available():
                    torch.set_default_device("cpu")

            # Convert PIL frames to numpy arrays for moviepy
            frame_arrays = []
            for frame in video_frames:
                frame_array = np.array(frame)
                frame_arrays.append(frame_array)

            # Create video clip with appropriate FPS (HunyuanVideo typically uses higher FPS than CogVideoX)
            fps = video_config.get("fps", 25)  # HunyuanVideo can handle higher FPS
            clip_sequence.append(ImageSequenceClip(frame_arrays, fps=fps))

            logger.info(
                f"Generated video clip {i + 1} with {len(frame_arrays)} frames at {fps} FPS"
            )

            # Clear CUDA cache after each generation to prevent memory accumulation
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                logger.info("Cleared CUDA cache after video generation")

        return clip_sequence


class ContentSafetyModel:
    def __init__(self) -> None:
        self.model = EnhancedTextModel(config.model.content_safety.safety_model)

    async def check_content(self, content: str) -> dict[str, Any]:
        prompt = f"""
        Analyze the following content for safety and appropriateness:
        {content}

        Provide a detailed analysis including:
        1. Content safety assessment
        2. Age appropriateness
        3. Potential concerns
        4. Recommendations for improvement
        """
        analysis = await self.model.generate(prompt, "You are a content safety analyzer.")
        return {"analysis": analysis}


class ScientificAccuracyModel:
    def __init__(self) -> None:
        self.model = EnhancedTextModel(config.model.content_safety.scientific_accuracy)

    async def check_accuracy(self, content: str) -> dict[str, Any]:
        prompt = f"""
        Analyze the following content for scientific accuracy:
        {content}

        Provide a detailed analysis including:
        1. Scientific accuracy assessment
        2. Factual correctness
        3. Potential misconceptions
        4. Recommendations for improvement
        """
        analysis = await self.model.generate(prompt, "You are a scientific accuracy analyzer.")
        return {"analysis": analysis}


class StoryAnalysisModel:
    def __init__(self) -> None:
        self.model = EnhancedTextModel(config.model.text_generation.story)

    async def analyze_story(self, text: str) -> dict[str, Any]:
        prompt = f"""
        Analyze the following children's story:
        {text}

        Provide analysis on:
        1. Story structure
        2. Character development
        3. Plot consistency
        4. Educational value
        5. Engagement level

        Provide specific suggestions for improvement.
        """

        analysis = await self.model.generate(prompt, "You are a children's story analyzer.")
        return {
            "analysis": analysis,
            "suggestions": analysis.split("\n\n")[-1] if "\n\n" in analysis else "",
        }

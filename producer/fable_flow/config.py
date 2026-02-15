from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from loguru import logger
from omegaconf import OmegaConf
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class ModelServerConfig(BaseModel):
    url: str = "http://localhost:8000/v1"
    api_key: str = "dev-api-key"
    timeout: float = 600.0
    max_retries: int = 3
    retry_delay: float = 2.0


class ImageGenerationConfig(BaseModel):
    # Default: FLUX 2 (native image-to-image conditioning baked in).
    # Options ordered by VRAM cost (with cpu_offload="model"):
    #   - black-forest-labs/FLUX.2-dev               full quality; tight on 80GB
    #   - black-forest-labs/FLUX.2-klein-9B          ~22GB; comfortable on 80GB
    #   - black-forest-labs/FLUX.2-klein-9b-fp8      ~10GB; great middle ground
    #   - black-forest-labs/FLUX.2-klein-9b-nvfp4    ~6GB;  smallest FLUX 2
    #   - black-forest-labs/FLUX.2-klein-4B          ~12GB
    #   - black-forest-labs/FLUX.1-dev               ~12GB; legacy, XLabs IP-Adapter
    #   - stabilityai/stable-diffusion-3.5-large     ~18GB
    #   - stabilityai/stable-diffusion-xl-base-1.0   ~8GB
    model: str = "black-forest-labs/FLUX.2-dev"

    # GPU memory strategy:
    #   - "model"      : default. Diffusers' enable_model_cpu_offload — one
    #                    submodel on GPU at a time. Required for FLUX.2-dev to
    #                    fit in 80GB.
    #   - "sequential" : enable_sequential_cpu_offload — layer-by-layer offload,
    #                    ~3x slower but fits FLUX.2-dev in <10GB. Use on smaller
    #                    GPUs (24-48GB) or when sharing VRAM.
    #   - "none"       : keep everything on GPU. Fastest. Only viable for small
    #                    quantized variants (klein-fp8/nvfp4) on an 80GB card.
    # IMPORTANT: never call .to(device) when an offload is enabled — the offload
    # owns GPU placement. The loader enforces this.
    cpu_offload: str = "model"


class TextToSpeechConfig(BaseModel):
    voice_preset: str = "af_heart"
    sample_rate: int = 24000
    lang_code: str = "a"  # 'a' = American English in Kokoro


class MusicGenerationConfig(BaseModel):
    model: str = "facebook/musicgen-small"


class VideoGenerationConfig(BaseModel):
    # Options:
    # - "Wan-AI/Wan2.1-I2V-14B-720P-Diffusers" (default; SOTA-tier I2V, ~25GB VRAM)
    # - "Wan-AI/Wan2.1-I2V-14B-480P-Diffusers" (smaller / faster)
    # - "hunyuanvideo-community/HunyuanVideo-I2V" (alternative; ~30GB VRAM)
    model: str = "Wan-AI/Wan2.1-I2V-14B-720P-Diffusers"
    height: int = 720
    width: int = 1280
    num_frames: int = 81  # Wan default; HunyuanVideo accepts up to 129
    num_inference_steps: int = 40
    guidance_scale: float = 5.0  # Wan default; HunyuanVideo uses 1.0 internally
    true_cfg_scale: float = 6.0  # HunyuanVideo-specific; ignored by Wan
    fps: int = 16  # Wan native fps; HunyuanVideo uses 24-25
    negative_prompt: str = (
        "scary faces, frightening expressions, dark shadows, aggressive poses, "
        "angry expressions, menacing looks, threatening gestures, unsafe situations, "
        "sharp objects, dangerous activities, crying children, distressed expressions, "
        "conflict scenes, fighting, violence, inappropriate content, adult themes, "
        "realistic violence, disturbing imagery, distorted faces, extra limbs, "
        "deformed body, blurry, low quality, watermark, text, logo"
    )


class ContinuationConfig(BaseModel):
    enabled: bool = True
    max_continuations: int = 5
    chunk_size: int = 32000


class ModelConfig(BaseModel):
    server: ModelServerConfig = Field(default_factory=ModelServerConfig)
    default: str = "google/gemma-4-31B-it"
    max_tokens: int = 64000
    stream: bool = False
    temperature: float = 0.8
    continuation: ContinuationConfig = Field(default_factory=ContinuationConfig)
    image_generation: ImageGenerationConfig = Field(default_factory=ImageGenerationConfig)
    text_to_speech: TextToSpeechConfig = Field(default_factory=TextToSpeechConfig)
    music_generation: MusicGenerationConfig = Field(default_factory=MusicGenerationConfig)
    video_generation: VideoGenerationConfig = Field(default_factory=VideoGenerationConfig)


class PathsConfig(BaseModel):
    base: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent)
    output: Path = Field(default_factory=lambda: Path("output"))

    @field_validator("base", "output", mode="after")
    @classmethod
    def create_directories(cls, v: Path) -> Path:
        v.mkdir(parents=True, exist_ok=True)
        return v


class StyleConfig(BaseModel):
    illustration_style: str = "digital watercolor and ink, soft lighting, warm colors, cinematic"
    music_style: str = "gentle children's storybook music, soft electronic and orchestral blend"
    video_animation_style: str = "subtle natural motion, gentle camera drift, soft lighting"


class PDFConfig(BaseModel):
    """PDF book styling. Defaults sized for 6x9 trade paperback."""

    page_size: tuple[float, float] = (6 * 72, 9 * 72)
    margin: float = 0.5 * 72
    body_font: str = "Times-Roman"
    title_font: str = "Helvetica-Bold"
    body_font_size: int = 14
    title_font_size: int = 28
    chapter_font_size: int = 20
    line_height: float = 1.4
    image_max_width: float = 5.0 * 72
    image_max_height: float = 6.5 * 72
    title_color: str = "#1565C0"
    chapter_color: str = "#2E7D32"
    body_color: str = "#212121"


class BookConfig(BaseModel):
    """Book publication metadata."""

    author: str = "FableFlow AI"
    publisher: str = "FableFlow Publishing"
    publisher_location: str = "Sydney, Australia"
    publication_year: int = Field(default_factory=lambda: datetime.now().year)
    edition: str = "First Edition"
    isbn_pdf: str | None = None
    isbn_epub: str | None = None


class Settings(BaseSettings):
    model: ModelConfig = Field(default_factory=ModelConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)
    style: StyleConfig = Field(default_factory=StyleConfig)
    pdf: PDFConfig = Field(default_factory=PDFConfig)
    book: BookConfig = Field(default_factory=BookConfig)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    @classmethod
    def from_yaml(cls, yaml_path: str | Path) -> Settings:
        template_vars = {
            "MODEL_SERVER_URL": os.getenv("MODEL_SERVER_URL", "http://localhost:8000/v1"),
            "DEFAULT_MODEL": os.getenv("DEFAULT_MODEL", "google/gemma-4-31B-it"),
            "MODEL_API_KEY": os.getenv("MODEL_API_KEY", "dev-api-key"),
        }

        conf = OmegaConf.load(yaml_path)
        conf.env = template_vars
        resolved = OmegaConf.to_container(conf, resolve=True)
        return cls(**resolved)


def _load_config() -> Settings:
    yaml_path = Path(__file__).parent.parent.parent / "config" / "default.yaml"
    if yaml_path.exists():
        try:
            return Settings.from_yaml(yaml_path)
        except Exception as e:
            logger.warning(f"Falling back to defaults; failed to load {yaml_path}: {e}")
    return Settings()


config = _load_config()

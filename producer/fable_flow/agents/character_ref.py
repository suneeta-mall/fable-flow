"""CharacterReferenceAgent — generates canonical reference images per character.

Runs ONCE at the start of Phase 1, before any chapter illustrations. The output
images are used as IP-Adapter conditioning for every subsequent illustration so
the same character looks the same across the whole book.
"""

from __future__ import annotations

from pathlib import Path

from loguru import logger

from fable_flow.agents._image_prompts import (
    build_full_body_prompt,
    build_portrait_prompt,
)
from fable_flow.config import config
from fable_flow.schemas.book_content import CharacterReference
from fable_flow.schemas.input_spec import Character, CharacterRole


class CharacterReferenceAgent:
    """Generate 1 portrait + 1 full-body reference image per character."""

    def __init__(self, image_model, output_dir: Path | None = None) -> None:
        self.image_model = image_model
        self.output_dir = output_dir or Path("output")
        self.refs_dir = self.output_dir / "character_refs"
        self.refs_dir.mkdir(parents=True, exist_ok=True)

    def _safe_name(self, name: str) -> str:
        return "".join(c if c.isalnum() else "_" for c in name).lower()

    def _seed(self, name: str, view: str) -> int:
        h = 0
        for ch in name + view:
            h = (h * 131 + ord(ch)) & 0x7FFFFFFF
        return h

    async def generate_all(
        self,
        characters: list[Character],
        resume: bool = False,
    ) -> list[CharacterReference]:
        """Generate references for every named character. Minor characters skipped."""
        style = config.style.illustration_style
        out: list[CharacterReference] = []

        for char in characters:
            # Skip MINOR roles — they don't appear consistently enough to need refs.
            if char.role == CharacterRole.MINOR:
                continue

            slug = self._safe_name(char.name)
            portrait_path = self.refs_dir / f"{slug}_portrait.png"
            full_body_path = self.refs_dir / f"{slug}_full.png"

            if resume and portrait_path.exists():
                logger.info(f"CharRef: reusing portrait for {char.name}")
            else:
                logger.info(f"CharRef: generating portrait for {char.name}")
                portrait_bytes = await self.image_model.generate_image(
                    prompt=build_portrait_prompt(char, style),
                    width=768,
                    height=768,
                    seed=self._seed(char.name, "portrait"),
                )
                portrait_path.write_bytes(portrait_bytes)

            if resume and full_body_path.exists():
                logger.info(f"CharRef: reusing full-body for {char.name}")
            else:
                logger.info(f"CharRef: generating full-body for {char.name}")
                full_body_bytes = await self.image_model.generate_image(
                    prompt=build_full_body_prompt(char, style),
                    width=768,
                    height=1024,
                    seed=self._seed(char.name, "full"),
                )
                full_body_path.write_bytes(full_body_bytes)

            out.append(
                CharacterReference(
                    name=char.name,
                    portrait_path=str(portrait_path),
                    full_body_path=str(full_body_path),
                )
            )

        logger.info(f"CharRef: rendered references for {len(out)} characters")
        return out

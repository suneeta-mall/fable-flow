import asyncio
import re
import string
from pathlib import Path
from typing import Any, Optional

import openai
from autogen_core import (
    MessageContext,
    RoutedAgent,
    TopicId,
    message_handler,
    type_subscription,
)
from autogen_core.models import (
    ChatCompletionClient,
    SystemMessage,
    UserMessage,
)
from loguru import logger
from moviepy import AudioFileClip, VideoFileClip, concatenate_videoclips
from rich.console import Console
from rich.markdown import Markdown

from fable_flow.book_structure import BookStructureGenerator
from fable_flow.book_utils import BookContentProcessor
from fable_flow.client import FableFlowChatClient
from fable_flow.common import Manuscript
from fable_flow.config import config
from fable_flow.continuation import ContinuationService, MessageConverter
from fable_flow.epub import EPUBGenerator
from fable_flow.models import (
    ContentSafetyModel,
    EnhancedImageModel,
    EnhancedMusicModel,
    EnhancedTextModel,
    EnhancedTTSModel,
    EnhancedVideoModel,
)
from fable_flow.pdf import PDFGenerator
from fable_flow.story_formatter import StoryHTMLFormatter


class ChatCompletionResult:
    """Result object that matches autogen's expected interface."""

    def __init__(self, content: str):
        self.content = content


class EnhancedChatCompletionWrapper:
    """Wrapper for ChatCompletionClient that handles incomplete responses with robust continuation."""

    def __init__(self, client: ChatCompletionClient) -> None:
        """Initialize the wrapper with a robust continuation service."""
        self.client = client

        openai_client = FableFlowChatClient.create_http_client()
        self.openai_client = openai.AsyncClient(
            api_key=config.model.server.api_key,
            base_url=config.model.server.url,
            timeout=config.model.server.timeout,
            max_retries=config.model.server.max_retries,
            http_client=openai_client,
        )
        self.continuation_service = ContinuationService(self.openai_client, config.model.default)

    async def create(
        self,
        messages: list[dict[str, Any]],
        cancellation_token: Any | None = None,
        **kwargs: Any,
    ) -> ChatCompletionResult:
        """Main create method that automatically handles continuation using robust service."""
        dict_messages = MessageConverter.to_dict_format(messages)

        content, metadata = await self.continuation_service.generate_with_continuation(
            dict_messages,
            max_tokens=kwargs.get("max_tokens"),
            **{k: v for k, v in kwargs.items() if k not in ["max_continuations", "max_tokens"]},
        )

        logger.info(f"Enhanced wrapper completed: {metadata}")
        return ChatCompletionResult(content)


@type_subscription(topic_type=config.agent_types.author_friend)
class FriendProofReaderAgent(RoutedAgent):
    def __init__(
        self,
        output_dir: Path = Path(config.paths.output),
    ) -> None:
        super().__init__("Friend of the author of the story.")
        self._system_message = SystemMessage(content=config.prompts.author_friend)
        self._model = EnhancedTextModel(config.model.text_generation.proofreading)
        self.output_dir = output_dir

    @message_handler
    async def handle_intermediate_text(self, message: Manuscript, ctx: MessageContext) -> None:
        output_file = self.output_dir / "FR_story.txt"

        if output_file.exists():
            logger.info(
                f"{self.id.type}: Skipping processing - output file already exists: {output_file}"
            )
            Console().print(
                Markdown(f"### {self.id.type}: Skipping - {output_file.name} already exists")
            )

            existing_content = output_file.read_text(encoding="utf-8")
            await self.publish_message(
                Manuscript(story=existing_content, synopsis=message.synopsis),
                topic_id=TopicId(config.agent_types.critique, source=self.id.key),
            )
            return

        prompt = f"""
        The synopsis is:\n\n {message.synopsis}

        Story:\n\n {message.story}

        You are to proof read and edit the story to provide an improved version of the story.
        """

        llm_result = await self._model.generate(prompt, self._system_message.content)

        Console().print(Markdown(f"### {self.id.type}: "))
        Console().print(Markdown(llm_result))

        output_file.write_text(llm_result, encoding="utf-8")
        logger.info(f"{self.id.type}: Generated and saved {output_file}")

        await self.publish_message(
            Manuscript(story=llm_result, synopsis=message.synopsis),
            topic_id=TopicId(config.agent_types.critique, source=self.id.key),
        )


@type_subscription(topic_type=config.agent_types.critique)
class CritiqueAgent(RoutedAgent):
    def __init__(
        self,
        model_client: ChatCompletionClient,
        output_dir: Path = Path(config.paths.output),
    ) -> None:
        super().__init__("An external reviewer to critically review the story.")
        self._system_message = SystemMessage(content=config.prompts.critical_reviewer)
        self._model_client = EnhancedChatCompletionWrapper(model_client)
        self.output_dir = output_dir

    @message_handler
    async def handle_intermediate_text(self, message: Manuscript, ctx: MessageContext) -> None:
        output_file = self.output_dir / "CR_story.txt"

        if output_file.exists():
            logger.info(
                f"{self.id.type}: Skipping processing - output file already exists: {output_file}"
            )
            Console().print(
                Markdown(f"### {self.id.type}: Skipping - {output_file.name} already exists")
            )

            existing_content = output_file.read_text(encoding="utf-8")
            await self.publish_message(
                Manuscript(story=existing_content, synopsis=message.synopsis),
                topic_id=TopicId(config.agent_types.content_moderator, source=self.id.key),
            )
            return

        prompt = f"The synopsis is:\n\n {message.synopsis}.\n\n\n. Story\n\n: {message.story}\n\n. You are to critque read and subsequently edit the story to provide an improved version of the story. \n\n\n"

        llm_result = await self._model_client.create(
            messages=[
                self._system_message,
                UserMessage(content=prompt, source=self.id.key),
            ],
            cancellation_token=ctx.cancellation_token,
        )
        Console().print(Markdown(f"### {self.id.type}: "))
        Console().print(Markdown(llm_result.content))

        output_file.write_text(llm_result.content, encoding="utf-8")
        logger.info(f"{self.id.type}: Generated and saved {output_file}")

        await self.publish_message(
            Manuscript(story=llm_result.content, synopsis=message.synopsis),
            topic_id=TopicId(config.agent_types.content_moderator, source=self.id.key),
        )


@type_subscription(topic_type=config.agent_types.content_moderator)
class ContentModeratorAgent(RoutedAgent):
    def __init__(
        self,
        output_dir: Path = Path(config.paths.output),
    ) -> None:
        super().__init__("A content moderator to critically review and edit the story.")
        self._system_message = SystemMessage(content=config.prompts.content_moderator)
        self._model = EnhancedTextModel(config.model.text_generation.content_moderation)
        self._safety_checker = ContentSafetyModel()
        self.output_dir = output_dir

    @message_handler
    async def handle_intermediate_text(self, message: Manuscript, ctx: MessageContext) -> None:
        output_file = self.output_dir / "CM_story.txt"

        if output_file.exists():
            logger.info(
                f"{self.id.type}: Skipping processing - output file already exists: {output_file}"
            )
            Console().print(
                Markdown(f"### {self.id.type}: Skipping - {output_file.name} already exists")
            )

            existing_content = output_file.read_text(encoding="utf-8")
            await self.publish_message(
                Manuscript(story=existing_content, synopsis=message.synopsis),
                topic_id=TopicId(config.agent_types.editor, source=self.id.key),
            )
            return

        safety_check = await self._safety_checker.check_content(message.story)

        prompt = f"""
        The synopsis is:\n\n {message.synopsis}

        Story:\n\n {message.story}

        Safety Analysis:\n\n {safety_check["analysis"]}

        You are to review the story and edit as needed to moderate the content to provide an improved version of the story.
        Consider the safety analysis and suggestions provided.
        """

        llm_result = await self._model.generate(prompt, self._system_message.content)

        Console().print(Markdown(f"### {self.id.type}: "))
        Console().print(Markdown(llm_result))

        output_file.write_text(llm_result, encoding="utf-8")
        logger.info(f"{self.id.type}: Generated and saved {output_file}")

        await self.publish_message(
            Manuscript(story=llm_result, synopsis=message.synopsis),
            topic_id=TopicId(config.agent_types.editor, source=self.id.key),
        )


@type_subscription(topic_type=config.agent_types.editor)
class EditorAgent(RoutedAgent):
    def __init__(
        self,
        model_client: ChatCompletionClient,
        output_dir: Path = Path(config.paths.output),
    ) -> None:
        super().__init__("The editor of the story.")
        self._system_message = SystemMessage(content=config.prompts.editor)
        self._model_client = EnhancedChatCompletionWrapper(model_client)
        self.output_dir = output_dir

    @message_handler
    async def handle_intermediate_text(self, message: Manuscript, ctx: MessageContext) -> None:
        output_file = self.output_dir / "ED_story.txt"

        if output_file.exists():
            logger.info(
                f"{self.id.type}: Skipping processing - output file already exists: {output_file}"
            )
            Console().print(
                Markdown(f"### {self.id.type}: Skipping - {output_file.name} already exists")
            )

            existing_content = output_file.read_text(encoding="utf-8")
            await self.publish_message(
                Manuscript(story=existing_content, synopsis=message.synopsis),
                topic_id=TopicId(config.agent_types.format_proof, source=self.id.key),
            )
            return

        prompt = f"The synopsis is:\n\n {message.synopsis}.\n\n\n. Story\n\n: {message.story}\n\n. As an editor, you are to review the story and edit as needed. \n\n\n"

        llm_result = await self._model_client.create(
            messages=[
                self._system_message,
                UserMessage(content=prompt, source=self.id.key),
            ],
            cancellation_token=ctx.cancellation_token,
        )
        Console().print(Markdown(f"### {self.id.type}: "))
        Console().print(Markdown(llm_result.content))

        output_file.write_text(llm_result.content, encoding="utf-8")
        logger.info(f"{self.id.type}: Generated and saved {output_file}")

        await self.publish_message(
            Manuscript(story=llm_result.content, synopsis=message.synopsis),
            topic_id=TopicId(config.agent_types.format_proof, source=self.id.key),
        )


@type_subscription(topic_type=config.agent_types.format_proof)
class FormatProofAgent(RoutedAgent):
    def __init__(
        self,
        model_client: ChatCompletionClient,
        output_dir: Path = Path(config.paths.output),
    ) -> None:
        super().__init__("A format & proof agent.")
        self._system_message = SystemMessage(content=config.prompts.proof_agent)
        self._model_client = EnhancedChatCompletionWrapper(model_client)
        self.output_dir = output_dir

    @message_handler
    async def handle_intermediate_text(self, message: Manuscript, ctx: MessageContext) -> None:
        output_file = self.output_dir / "final_proof_story.txt"

        if output_file.exists():
            logger.info(
                f"{self.id.type}: Skipping processing - output file already exists: {output_file}"
            )
            Console().print(
                Markdown(f"### {self.id.type}: Skipping - {output_file.name} already exists")
            )

            existing_content = output_file.read_text(encoding="utf-8")
            await self.publish_message(
                Manuscript(story=existing_content, synopsis=message.synopsis),
                topic_id=TopicId(config.agent_types.user, source=self.id.key),
            )
            return

        prompt = f"Draft copy:\n{message.story}."
        llm_result = await self._model_client.create(
            messages=[
                self._system_message,
                UserMessage(content=prompt, source=self.id.key),
            ],
            cancellation_token=ctx.cancellation_token,
        )
        Console().print(Markdown(f"### {self.id.type}: "))
        Console().print(Markdown(llm_result.content))

        output_file.write_text(llm_result.content, encoding="utf-8")
        logger.info(f"{self.id.type}: Generated and saved {output_file}")

        await self.publish_message(
            Manuscript(story=llm_result.content, synopsis=message.synopsis),
            topic_id=TopicId(config.agent_types.user, source=self.id.key),
        )


@type_subscription(topic_type=config.agent_types.user)
class UserAgent(RoutedAgent):
    def __init__(self, output_dir: Path = Path(config.paths.output)) -> None:
        super().__init__("A user agent that approves or reject edits and compiles manuscript.")
        self.output_dir = output_dir

    @message_handler
    async def handle_final_copy(self, message: Manuscript, ctx: MessageContext) -> None:
        (self.output_dir / "final_story.txt").write_text(message.story, encoding="utf-8")
        user_input = input("Enter your message, type 'Y/N' to conclude the task: ")

        Console().print(Markdown(f"### {self.id.type}: "))
        Console().print(Markdown(user_input))

        if user_input.lower().strip(string.punctuation) == "y":
            Console().print(Markdown("Manuscript is approved"))

            await self.publish_message(
                message,
                topic_id=TopicId(config.agent_types.narrator, source=self.id.key),
            )
            await self.publish_message(
                message,
                topic_id=TopicId(config.agent_types.illustration_planner, source=self.id.key),
            )


@type_subscription(topic_type=config.agent_types.narrator)
class NarratorAgent(RoutedAgent):
    def __init__(
        self,
        voice_id: str = "default",
        output_dir: Path = Path(config.paths.output),
    ) -> None:
        super().__init__("The narrator of the story.")
        self._tts_model = EnhancedTTSModel()
        self.voice_id = voice_id
        self.output_dir = output_dir

    @message_handler
    async def handle_final_copy(self, message: Manuscript, ctx: MessageContext) -> None:
        output_file = self.output_dir / "narration.m4a"

        if output_file.exists():
            logger.info(
                f"{self.id.type}: Skipping processing - output file already exists: {output_file}"
            )
            Console().print(
                Markdown(f"### {self.id.type}: Skipping - {output_file.name} already exists")
            )
            return

        Console().print(
            Markdown(
                f"### {self.id.type}: Generating speech for story ({len(message.story)} characters)..."
            )
        )
        audio = await self._tts_model.generate_speech(message.story, self.voice_id)
        output_file.write_bytes(audio)

        file_size_mb = len(audio) / (1024 * 1024)
        Console().print(Markdown(f"✅ Generated narration audio ({file_size_mb:.1f}MB)"))
        logger.info(f"{self.id.type}: Generated and saved {output_file} ({file_size_mb:.1f}MB)")


@type_subscription(topic_type=config.agent_types.illustration_planner)
class IllustrationPlannerAgent(RoutedAgent):
    def __init__(
        self,
        model_client: ChatCompletionClient,
        output_dir: Path = Path(config.paths.output),
    ) -> None:
        super().__init__("An agent that plans images for the story.")
        self._system_message = SystemMessage(content=config.prompts.image_planner)
        self._model_client = EnhancedChatCompletionWrapper(model_client)
        self.output_dir = output_dir

    @message_handler
    async def handle_intermediate_text(self, message: Manuscript, ctx: MessageContext) -> None:
        output_file = self.output_dir / "image_planner_story.txt"

        if output_file.exists():
            logger.info(
                f"{self.id.type}: Skipping processing - output file already exists: {output_file}"
            )
            Console().print(
                Markdown(f"### {self.id.type}: Skipping - {output_file.name} already exists")
            )

            existing_content = output_file.read_text(encoding="utf-8")
            await self.publish_message(
                Manuscript(story=existing_content, synopsis=message.synopsis),
                topic_id=TopicId(config.agent_types.illustrator, source=self.id.key),
            )
            return

        Console().print(Markdown(f"### {self.id.type}: Planning illustrations chapter-by-chapter"))
        logger.info(f"{self.id.type}: Starting chapter-by-chapter illustration planning")

        # Read exact approved text from final_story.txt
        final_story_path = self.output_dir / "final_story.txt"
        if not final_story_path.exists():
            logger.warning(
                f"{self.id.type}: final_story.txt not found, using message.story as fallback"
            )
            final_story_text = message.story
        else:
            final_story_text = final_story_path.read_text(encoding="utf-8")
            logger.info(f"{self.id.type}: Read {len(final_story_text)} chars from final_story.txt")

        # Split story into chapters
        formatter = StoryHTMLFormatter(final_story_text)
        chapters = formatter.detect_chapters(final_story_text)
        logger.info(f"{self.id.type}: Split story into {len(chapters)} chapter(s)")

        # Process each chapter to add image markup
        chapters_with_images = []
        for i, (chapter_title, chapter_content) in enumerate(chapters):
            logger.info(
                f"{self.id.type}: Planning illustrations for chapter {i + 1}/{len(chapters)}: {chapter_title}"
            )
            Console().print(
                Markdown(
                    f"Planning images for chapter {i + 1}/{len(chapters)}: **{chapter_title}**"
                )
            )

            chapter_with_images = await self._plan_images_for_chapter(
                chapter_title, chapter_content, i + 1, len(chapters), ctx
            )
            chapters_with_images.append((chapter_title, chapter_with_images))

        # Reconstruct full story with chapter markers and images
        # Pass original story to preserve title/subtitle
        story_with_images = self._reconstruct_story_with_chapters(
            chapters_with_images, final_story_text
        )

        Console().print(Markdown(f"### {self.id.type}: Illustration planning complete"))
        logger.info(f"{self.id.type}: Generated story with images ({len(story_with_images)} chars)")

        # Write to file
        output_file.write_text(story_with_images, encoding="utf-8")
        logger.info(f"{self.id.type}: Saved to {output_file}")

        # Publish to illustrator
        await self.publish_message(
            Manuscript(story=story_with_images, synopsis=message.synopsis),
            topic_id=TopicId(config.agent_types.illustrator, source=self.id.key),
        )

    async def _plan_images_for_chapter(
        self,
        chapter_title: str,
        chapter_content: str,
        chapter_num: int,
        total_chapters: int,
        ctx: MessageContext,
    ) -> str:
        """Plan and insert image markup for a single chapter.

        Uses LLM to determine where images should go and insert <image> tags
        while preserving the exact chapter text.

        Args:
            chapter_title: The chapter title
            chapter_content: The exact chapter content from final_story.txt
            chapter_num: Current chapter number
            total_chapters: Total number of chapters
            ctx: Message context

        Returns:
            Chapter content with <image> markup inserted
        """
        prompt = f"""
You are planning illustrations for Chapter {chapter_num} of {total_chapters} in a children's book.

🚨 CRITICAL RULES 🚨

1. DO NOT CHANGE ANY WORDS from the chapter text - preserve it EXACTLY
2. ONLY insert <image> tags to mark where images should appear
3. DO NOT modify, add, or remove any story text
4. Each image should enhance the story and engage young readers

Image markup format:
<image>NUMBER [detailed description for image generation]</image>

Guidelines for planning images:
- Place 1-3 images per chapter (don't overdo it)
- Insert images at natural breaks in the narrative
- Describe what should be illustrated (characters, setting, action, emotions)
- Number images sequentially starting from {(chapter_num - 1) * 3 + 1}
- Each description should be detailed enough for an illustrator to create the image
- Consider: characters present, setting details, key actions, emotional moments

CHAPTER TITLE: {chapter_title}

CHAPTER TEXT (PRESERVE EXACTLY):
---
{chapter_content}
---

YOUR TASK:
1. Read through the chapter carefully
2. Identify 1-3 moments that would benefit from illustration
3. Insert <image>N [detailed description]</image> tags at those points
4. Keep ALL the original text exactly as it is

OUTPUT:
Return the chapter text with <image> tags inserted at appropriate positions.
Place each <image> tag on its own line.
"""

        llm_result = await self._model_client.create(
            messages=[
                SystemMessage(
                    content="You are an illustration planner for children's books. You insert image markup into story text without changing any of the story words. You only add image tags with detailed descriptions."
                ),
                UserMessage(content=prompt, source=self.id.key),
            ],
            cancellation_token=ctx.cancellation_token,
        )

        chapter_with_images = llm_result.content.strip()

        # Count images added
        image_count = len(re.findall(r"<image>", chapter_with_images))
        logger.info(f"{self.id.type}: Added {image_count} image(s) to chapter {chapter_num}")

        return chapter_with_images

    def _reconstruct_story_with_chapters(
        self, chapters: list[tuple[str, str]], original_story: str = None
    ) -> str:
        """Reconstruct full story from chapters with proper chapter markers.

        Preserves the book title and subtitle from the original story to avoid
        the first chapter being mistaken for the book title.

        Args:
            chapters: List of (chapter_title, chapter_content) tuples
            original_story: Optional original story text to extract title/subtitle from

        Returns:
            Full story text with book title, subtitle, and ## Chapter markers
        """
        story_parts = []

        # Extract and preserve book title and subtitle from original story
        if original_story:
            lines = original_story.split("\n")
            for line in lines:
                stripped = line.strip()
                # Include title and subtitle lines (before first Chapter)
                if stripped.startswith("#") and "chapter" not in stripped.lower():
                    story_parts.append(line)
                elif stripped == "---":
                    story_parts.append(line)
                elif stripped.startswith("## Chapter") or stripped.startswith("Chapter"):
                    # Stop when we hit the first chapter
                    break
                elif not stripped and story_parts:
                    # Preserve empty lines in the header
                    story_parts.append("")

            # Add separator before chapters
            if story_parts:
                story_parts.append("")

        # Add all chapters
        for chapter_title, chapter_content in chapters:
            # Add chapter marker
            story_parts.append(f"## {chapter_title}")
            story_parts.append("")  # Empty line after chapter title
            story_parts.append(chapter_content.strip())
            story_parts.append("")  # Empty line between chapters
            story_parts.append("")  # Double empty line between chapters

        return "\n".join(story_parts)


@type_subscription(topic_type=config.agent_types.illustrator)
class IllustratorAgent(RoutedAgent):
    def __init__(
        self,
        output_dir: Path = Path(config.paths.output),
    ) -> None:
        super().__init__("An illustrator for the story.")
        self._system_message = SystemMessage(content=config.prompts.illustrator)
        self._model = EnhancedTextModel(config.model.text_generation.story)
        self._image_model = EnhancedImageModel()
        self.output_dir = output_dir

    async def _image_gen(
        self,
        character_appearence: str,
        style_attributes: str,
        worn_and_carried: str,
        scenario: str,
    ) -> bytes:
        prompt = f"""
        A children's book illustration of:
        Character: {character_appearence}
        Style: {style_attributes}
        Items: {worn_and_carried}
        Scene: {scenario}
        """

        return await self._image_model.generate_image(prompt, config.style.illustration)

    async def _generate_cover_images(self, message: Manuscript) -> None:
        """Generate front and back cover images if they don't exist.

        Uses the PDF page_size from config to maintain correct aspect ratio for covers.
        """
        front_cover_path = self.output_dir / "front_cover.png"
        back_cover_path = self.output_dir / "back_cover.png"

        # Calculate cover dimensions based on PDF page_size aspect ratio
        # PDF page_size is in points (e.g., 6*72 x 9*72 = 432x648)
        page_width, page_height = config.style.pdf.page_size
        aspect_ratio = page_width / page_height

        # Use high resolution for quality while maintaining aspect ratio
        # Target height of 1536 pixels for good quality
        cover_height = 1536
        cover_width = int(cover_height * aspect_ratio)

        logger.info(
            f"IllustratorAgent: Using cover dimensions {cover_width}x{cover_height} "
            f"(aspect ratio {aspect_ratio:.2f} from PDF page_size {page_width}x{page_height})"
        )

        if not front_cover_path.exists():
            try:
                title_info = (
                    message.synopsis[:100] if message.synopsis else "children's educational story"
                )
                front_cover_prompt = f"""children's book cover with background suitable for title overlay: watercolor style, soft pastels, no humans, scene inspired by "{title_info}". CRITICAL: absolutely NO text, letters, words, titles, writing of any kind - pure art only."""

                front_cover_data = await self._image_model.generate_image(
                    front_cover_prompt,
                    config.style.illustration,
                    width=cover_width,
                    height=cover_height,
                )
                front_cover_path.write_bytes(front_cover_data)
                logger.info(f"IllustratorAgent: Generated front cover: {front_cover_path}")
                Console().print(f"Generated front cover: {front_cover_path}")
            except Exception as e:
                logger.error(f"IllustratorAgent: Failed to generate front cover: {e}")
        else:
            logger.info(f"IllustratorAgent: Front cover already exists: {front_cover_path}")

        if not back_cover_path.exists():
            try:
                back_cover_prompt = """
                Children's book back cover: simple watercolor pattern, very soft colors, no humans, no text, subtle abstract design. Clear space for text overlay.
                """

                back_cover_data = await self._image_model.generate_image(
                    back_cover_prompt,
                    config.style.illustration,
                    width=cover_width,
                    height=cover_height,
                )
                back_cover_path.write_bytes(back_cover_data)
                logger.info(f"IllustratorAgent: Generated back cover: {back_cover_path}")
                Console().print(f"Generated back cover: {back_cover_path}")
            except Exception as e:
                logger.error(f"IllustratorAgent: Failed to generate back cover: {e}")
        else:
            logger.info(f"IllustratorAgent: Back cover already exists: {back_cover_path}")

    @message_handler
    async def handle_request_to_illustrate(self, message: Manuscript, ctx: MessageContext) -> None:
        logger.info(f"IllustratorAgent: Received story with {len(message.story)} characters")

        await self._generate_cover_images(message)

        image_prompts = re.findall(r"<image>(.*?)</image>", message.story, re.DOTALL)
        logger.info(f"IllustratorAgent: Found {len(image_prompts)} image prompts in the story.")

        Console().print(Markdown(f"### {self.id.type}: "))
        images: list[str] = []
        for i, image_prompt in enumerate(image_prompts):
            try:
                image_path = self.output_dir / f"image_{i}.png"

                if image_path.exists():
                    logger.info(
                        f"IllustratorAgent: Skipping image {i} - already exists: {image_path}"
                    )
                    Console().print(f"Skipping image {i} (already exists): {image_path}")
                    images.append(str(image_path))
                    continue

                logger.info(
                    f"IllustratorAgent: Generating image {i} for prompt: {image_prompt.strip()[:100]}..."
                )
                image_data = await self._image_gen(
                    character_appearence="child character",
                    style_attributes="children's book illustration",
                    worn_and_carried="",
                    scenario=image_prompt.strip(),
                )

                image_path.write_bytes(image_data)
                images.append(str(image_path))

                logger.info(f"IllustratorAgent: Generated and saved image {i}: {image_path}")
                Console().print(f"Generated image {i}: {image_path}")
            except Exception as e:
                logger.error(f"IllustratorAgent: Failed to generate image {i}: {e}")
                continue

        message.images = images
        logger.info(f"IllustratorAgent: Attached {len(images)} images to message")

        await self.publish_message(
            message,
            topic_id=TopicId(config.agent_types.producer, source=self.id.key),
        )
        await self.publish_message(
            message,
            topic_id=TopicId(config.agent_types.movie_director_type, source=self.id.key),
        )


@type_subscription(topic_type=config.agent_types.producer)
class BookProducerAgent(RoutedAgent):
    def __init__(
        self,
        model_client: ChatCompletionClient,
        output_dir: Path = Path(config.paths.output),
    ) -> None:
        super().__init__("Producer of the book.")
        self._system_message = SystemMessage(content=config.prompts.book_producer)
        self._model_client = EnhancedChatCompletionWrapper(model_client)
        self.output_dir = output_dir
        self._pdf_generator = PDFGenerator(output_dir)
        self._epub_generator = EPUBGenerator(output_dir)

    @message_handler
    async def handle_intermediate_text(self, message: Manuscript, ctx: MessageContext) -> None:
        Console().print(Markdown(f"### {self.id.type}: "))

        formatted_book_path = self.output_dir / "formatted_book.html"
        if formatted_book_path.exists():
            logger.info("BookProducerAgent: Using existing formatted_book.html")
            Console().print(
                Markdown("Using existing formatted_book.html - review and edit if needed")
            )
        else:
            # Generate new HTML content
            Console().print(
                Markdown(
                    "Creating professionally formatted children's book with formal structure (PDF + EPUB)..."
                )
            )
            formatted_content = await self._generate_formatted_book_content(message, ctx)

            formatted_book_path.write_text(formatted_content, encoding="utf-8")
            Console().print(Markdown("### Book Content Generated! 📚"))
            Console().print(Markdown(f"✅ Content saved to: `{formatted_book_path}`"))

        Console().print(Markdown("### 📝 Review & Edit Your Book"))
        Console().print(Markdown(f"**File to review:** `{formatted_book_path}`"))
        Console().print(
            Markdown(
                "Please review and edit the book content as needed using your preferred editor."
            )
        )

        user_input = input(
            "\nHave you finished reviewing/editing? Enter 'y' to proceed with final book production: "
        )

        if user_input.lower().strip() in ["y", "yes"]:
            formatted_content = formatted_book_path.read_text(encoding="utf-8")
            Console().print(Markdown("✅ Proceeding with final book production..."))

            await self._generate_book_outputs(formatted_content, message, ctx)
        else:
            Console().print(
                Markdown("❌ Book production cancelled. Edit the file and run again when ready.")
            )
            logger.info("BookProducerAgent: Book production cancelled by user")
            return

    async def _generate_formatted_book_content(
        self, message: Manuscript, ctx: MessageContext
    ) -> str:
        """Generate the complete formatted book HTML content - SIMPLIFIED APPROACH.

        Now that IllustrationPlannerAgent properly merges exact text + images,
        this method is much simpler:
        1. Read image_planner_story.txt (has exact text + image markup)
        2. Split by chapters
        3. Format each chapter with HTML markup for styling
        4. Stitch together with ToC, Preface, Back Matter

        image_planner_story.txt is the single source of truth!
        """
        logger.info("BookProducerAgent: Starting chapter-by-chapter HTML generation (SIMPLIFIED)")

        # Step 1: Read story with images from image_planner_story.txt
        # IllustrationPlannerAgent has already merged exact text + images
        image_planner_path = self.output_dir / "image_planner_story.txt"

        if not image_planner_path.exists():
            raise FileNotFoundError(
                f"image_planner_story.txt not found in {self.output_dir}. "
                "Please run IllustrationPlannerAgent first."
            )

        story_with_images = image_planner_path.read_text(encoding="utf-8")
        logger.info(
            f"BookProducerAgent: Read {len(story_with_images)} chars from image_planner_story.txt"
        )

        # Count images
        image_count = len(re.findall(r"<image>", story_with_images))
        logger.info(f"BookProducerAgent: Found {image_count} image markup(s)")

        # Step 2: Split into chapters
        formatter = StoryHTMLFormatter(story_with_images)
        chapters = formatter.detect_chapters(story_with_images)
        logger.info(f"BookProducerAgent: Split story into {len(chapters)} chapter(s)")

        # Step 3: Generate and validate book metadata
        book_metadata = await self._generate_book_metadata(message, ctx)
        book_metadata = BookContentProcessor.validate_book_metadata(book_metadata)

        # Step 4: Format each chapter with HTML markup (no merging needed!)
        formatted_chapters = []
        for i, (chapter_title, chapter_content) in enumerate(chapters):
            logger.info(
                f"BookProducerAgent: Formatting chapter {i + 1}/{len(chapters)}: {chapter_title}"
            )

            chapter_html = await self._format_chapter_with_llm(
                chapter_title, chapter_content, i + 1, len(chapters), ctx
            )
            formatted_chapters.append(chapter_html)

        # Step 5: Stitch all chapters together
        story_chapters_html = "\n".join(formatted_chapters)
        logger.info(
            f"BookProducerAgent: Stitched {len(formatted_chapters)} chapters into {len(story_chapters_html)} chars"
        )

        # Step 6: Create unified structure generator for covers, title page, publication info
        structure_gen = BookStructureGenerator(self.output_dir, book_metadata, format="pdf")
        logger.info("BookProducerAgent: Using BookStructureGenerator for consistent front matter")

        # Step 7: Generate ToC, Preface, and Back Matter using LLM
        toc_and_preface_html = await self._generate_toc_and_preface(
            story_chapters_html, book_metadata, message, ctx
        )
        back_matter_html = await self._generate_back_matter(
            story_with_images, book_metadata, message, ctx
        )

        # Step 8: Assemble complete book structure
        story_content = toc_and_preface_html + story_chapters_html + back_matter_html

        # Step 9: Assemble complete book using structure generator
        formatted_content = structure_gen.generate_complete_book_structure(story_content)

        # Step 10: Verify and fix author attribution
        formatted_content = BookContentProcessor.verify_and_fix_author_attribution(
            formatted_content
        )

        logger.info(
            f"BookProducerAgent: Generated complete book with {len(formatted_content)} characters"
        )
        return formatted_content

    async def _format_chapter_with_llm(
        self,
        chapter_title: str,
        chapter_content: str,
        chapter_num: int,
        total_chapters: int,
        ctx: MessageContext,
    ) -> str:
        """Format a single chapter with HTML markup using LLM.

        Uses a STRICT prompt that instructs the LLM to ONLY add HTML markup
        without changing any words. Small context per chapter reduces risk of modifications.

        Args:
            chapter_title: The chapter title
            chapter_content: The chapter content (plain text with image markup)
            chapter_num: Current chapter number
            total_chapters: Total number of chapters
            ctx: Message context

        Returns:
            HTML-formatted chapter wrapped in page-spread structure
        """
        prompt = f"""
You are formatting Chapter {chapter_num} of {total_chapters} for a children's book.

🚨 CRITICAL RULES - FOLLOW EXACTLY 🚨

1. DO NOT CHANGE ANY WORDS - Your ONLY job is to wrap existing text in HTML tags
2. DO NOT add, remove, or modify any text content
3. DO NOT summarize, paraphrase, or rewrite anything
4. PRESERVE all <image> tags EXACTLY as they appear
5. ONLY add HTML markup for styling and structure

Your job is to add HTML tags for:
- Dialogue (wrap in <span class="dialogue">"text"</span>)
- Questions (wrap in <span class="question">text?</span>)
- Emphasis (wrap in <em>text</em> or <strong>text</strong> where appropriate)
- Paragraphs (wrap in <p class="story-text">text</p>)
- Poems (if you see lines marked with *, wrap in <div class="poem-box"><p class="poem-verse">line1<br/>line2</p></div> and REMOVE the * markers)

Image markup format:
- Keep <image>NUMBER [description]</image> tags EXACTLY as provided
- The system will convert them to proper HTML later

CHAPTER TITLE: {chapter_title}

CHAPTER CONTENT (DO NOT MODIFY TEXT - ONLY ADD HTML TAGS):
---
{chapter_content}
---

OUTPUT FORMAT:
Return ONLY the chapter wrapped in this structure:

<div class="page-spread">
    <div class="page">
        <h2 class="chapter-title">{chapter_title}</h2>
        [Your HTML-wrapped content here with dialogue, paragraphs, images, etc.]
    </div>
</div>

Remember: PRESERVE THE EXACT WORDS. Only wrap them in HTML tags for styling.
"""

        logger.info(
            f"BookProducerAgent: Sending chapter {chapter_num} to LLM (context: {len(prompt)} chars)"
        )

        llm_result = await self._model_client.create(
            messages=[
                SystemMessage(
                    content="You are a precise HTML formatter. You ONLY add HTML markup tags around existing text. You NEVER change, add, or remove words from the original content."
                ),
                UserMessage(content=prompt, source=self.id.key),
            ],
            cancellation_token=ctx.cancellation_token,
        )

        chapter_html = BookContentProcessor.clean_html_content(llm_result.content)

        # Convert image markup to proper HTML with kid-friendly captions
        chapter_html = await self._convert_image_markup_to_html(
            chapter_html, chapter_title, chapter_content, ctx
        )

        logger.info(
            f"BookProducerAgent: Chapter {chapter_num} formatted ({len(chapter_html)} chars)"
        )

        return chapter_html

    async def _generate_kid_friendly_caption(
        self,
        image_prompt: str,
        surrounding_context: str,
        chapter_title: str,
        ctx: MessageContext,
    ) -> str:
        """Generate a kid-friendly caption for an image based on prompt and context.

        Args:
            image_prompt: The original illustrator prompt/description
            surrounding_context: Text surrounding the image for context
            chapter_title: The chapter title
            ctx: Message context

        Returns:
            Kid-friendly caption (1-2 short sentences)
        """
        prompt = f"""
Generate a SHORT, kid-friendly caption for an illustration in a children's book.

CHAPTER: {chapter_title}

IMAGE DESCRIPTION (for illustrator): {image_prompt}

STORY CONTEXT:
{surrounding_context}

REQUIREMENTS:
1. Write a caption that a child would understand and enjoy
2. Keep it SHORT - maximum 1-2 sentences, ideally under 15 words
3. Make it engaging and descriptive, not technical
4. Base it on what's happening in the story at this point
5. Don't just repeat the illustration description - derive meaning from context

GOOD EXAMPLES:
- "Luna discovers the magical forest path."
- "The friends share a delicious picnic under the old oak tree."
- "Max finds a mysterious glowing crystal."

BAD EXAMPLES (too technical/long):
- "A whimsical forest scene with tall trees, a winding path, and soft morning light filtering through leaves"
- "The illustration shows the characters sitting on a checkered blanket with various food items"

OUTPUT: Return ONLY the caption text, nothing else.
"""

        llm_result = await self._model_client.create(
            messages=[
                SystemMessage(
                    content="You are a children's book editor who writes engaging, kid-friendly image captions. Keep captions SHORT and delightful."
                ),
                UserMessage(content=prompt, source=self.id.key),
            ],
            cancellation_token=ctx.cancellation_token,
        )

        caption = llm_result.content.strip()
        # Remove any quotes that might have been added
        caption = caption.strip("\"'")

        logger.debug(f"BookProducerAgent: Generated kid-friendly caption: {caption}")

        return caption

    async def _convert_image_markup_to_html(
        self,
        html_content: str,
        chapter_title: str,
        chapter_content: str,
        ctx: MessageContext,
    ) -> str:
        """Convert <image>N [description]</image> markup to proper HTML img tags with kid-friendly captions.

        NOTE: Markup uses 1-based numbering but files are 0-based (image_0.png).

        Args:
            html_content: HTML content with image markup
            chapter_title: The chapter title for context
            chapter_content: The original chapter content for context
            ctx: Message context for LLM calls

        Returns:
            HTML content with proper img tags and kid-friendly captions
        """
        # Pattern: <image>NUMBER [description]</image>
        image_pattern = r"<image>\s*(\d+)\s*\[([^\]]+)\]</image>"

        # Find all images first to process them
        matches = list(re.finditer(image_pattern, html_content, flags=re.DOTALL))

        # Process each image and collect replacements
        replacements = []
        for match in matches:
            markup_number = int(match.group(1))
            description = match.group(2).strip()

            # Convert 1-based markup to 0-based filename
            file_number = markup_number - 1

            # Extract surrounding context (500 chars before and after the image)
            start_pos = max(0, match.start() - 500)
            end_pos = min(len(html_content), match.end() + 500)
            surrounding_text = html_content[start_pos:end_pos]

            # Strip HTML tags to get clean text context
            clean_context = re.sub(r"<[^>]+>", " ", surrounding_text)
            clean_context = re.sub(r"\s+", " ", clean_context).strip()

            # Generate kid-friendly caption
            caption = await self._generate_kid_friendly_caption(
                description, clean_context, chapter_title, ctx
            )

            # Use full-page layout as default
            html = f'''
<div class="image-full-page">
    <img src="image_{file_number}.png" alt="{description}">
    <div class="caption">{caption}</div>
</div>'''

            logger.debug(
                f"BookProducerAgent: Converting image {markup_number} -> image_{file_number}.png with caption: {caption}"
            )

            replacements.append((match.group(0), html))

        # Apply all replacements
        result = html_content
        for old, new in replacements:
            result = result.replace(old, new, 1)

        return result

    async def _generate_toc_and_preface(
        self, story_html: str, metadata: dict, message: Manuscript, ctx: MessageContext
    ) -> str:
        """Generate Table of Contents and Preface using LLM.

        Args:
            story_html: The formatted story HTML to extract chapter titles from
            metadata: Book metadata
            message: The manuscript message
            ctx: Message context

        Returns:
            HTML for ToC and Preface
        """
        # Extract chapter titles from the already-generated HTML
        import re

        from bs4 import BeautifulSoup

        soup = BeautifulSoup(story_html, "html.parser")
        chapter_titles = [
            h2.get_text().strip() for h2 in soup.find_all("h2", class_="chapter-title")
        ]

        logger.info(f"BookProducerAgent: Extracted {len(chapter_titles)} chapter titles for ToC")

        prompt = f"""
        Generate ONLY the Table of Contents and Preface for this children's book.

        DO NOT generate story chapters - those are already created.

        1. TABLE OF CONTENTS
           - List the following chapters: {", ".join(chapter_titles)}
           - Use page number placeholders (1, 5, 10, etc.)
           - Format: <div class="page-spread"><div class="page"><div class="table-of-contents"><h2>Table of Contents</h2>...</div></div></div>

        2. PREFACE
           - Brief and impactful (3-4 paragraphs max)
           - Explain the book's educational value
           - Encourage curiosity and learning
           - Format: <div class="page-spread"><div class="page"><div class="preface"><h2>Preface</h2>...</div></div></div>

        BOOK METADATA:
        Title: {metadata["title"]}
        Synopsis: {message.synopsis or "N/A"}
        Themes: {metadata.get("themes", "Learning, Adventure")}

        Generate professional HTML for these two sections only.
        """

        llm_result = await self._model_client.create(
            messages=[
                self._system_message,
                UserMessage(content=prompt, source=self.id.key),
            ],
            cancellation_token=ctx.cancellation_token,
        )

        toc_preface = BookContentProcessor.clean_html_content(llm_result.content)
        logger.info(f"BookProducerAgent: Generated ToC and Preface ({len(toc_preface)} chars)")
        return toc_preface

    async def _generate_back_matter(
        self, story_text: str, metadata: dict, message: Manuscript, ctx: MessageContext
    ) -> str:
        """Generate About the Author, Index, and Acknowledgments using LLM.

        Args:
            story_text: The original story text (for index generation)
            metadata: Book metadata
            message: The manuscript message
            ctx: Message context

        Returns:
            HTML for back matter sections
        """
        prompt = f"""
        Generate the following BACK MATTER sections for this children's book:

        1. ABOUT THE AUTHOR
           - Reference "{config.book.draft_story_author}" as original author
           - Mention "This story has been enhanced and expanded using FableFlow"
           - Format: <div class="page-spread"><div class="page"><div class="about-author"><h2>About the Author</h2>...</div></div></div>

        2. INDEX
           - Extract 15-25 key terms from the story (educational concepts, character names, important objects)
           - Alphabetical order with page number placeholders
           - Format: <div class="page-spread"><div class="page"><div class="index"><h2>Index</h2><div class="index-entry"><span class="term">Term</span><span class="page-refs">1, 5</span></div>...</div></div></div>

        3. ACKNOWLEDGMENTS
           - Acknowledge curious children, original author ({config.book.draft_story_author}), and educators
           - Inspire continued learning and curiosity
           - Format: <div class="page-spread"><div class="page"><div class="acknowledgments"><h2>Acknowledgments</h2>...</div></div></div>

        STORY EXCERPT (first 1000 chars for index generation):
        {story_text[:1000]}

        Generate professional HTML for these three sections.
        """

        llm_result = await self._model_client.create(
            messages=[
                SystemMessage(
                    content="You are a children's book publishing expert. Generate professional back matter sections."
                ),
                UserMessage(content=prompt, source=self.id.key),
            ],
            cancellation_token=ctx.cancellation_token,
        )

        back_matter = BookContentProcessor.clean_html_content(llm_result.content)
        logger.info(f"BookProducerAgent: Generated back matter ({len(back_matter)} chars)")
        return back_matter

    # OLD METHODS - Now handled by BookStructureGenerator
    # These are kept for backward compatibility but should not be used in new code

    async def _generate_book_outputs(
        self, formatted_content: str, message: Manuscript, ctx: MessageContext
    ) -> None:
        book_metadata = await self._generate_book_metadata(message, ctx)

        pdf_path = self.output_dir / "book.pdf"
        if not pdf_path.exists():
            self._pdf_generator.generate_pdf(formatted_content, message, pdf_path, book_metadata)
        else:
            logger.info("BookProducerAgent: Skipping PDF generation - book.pdf already exists")

        epub_path = self.output_dir / "book.epub"
        if not epub_path.exists():
            Console().print(Markdown("📚 Generating EPUB format..."))
            self._epub_generator.generate_epub(formatted_content, message, epub_path, book_metadata)
        else:
            logger.info("BookProducerAgent: Skipping EPUB generation - book.epub already exists")

        book_md_path = self.output_dir / "book.md"
        if not book_md_path.exists():
            await self._generate_book_markdown(message, ctx, book_metadata)
        else:
            logger.info("BookProducerAgent: Skipping book.md generation - book.md already exists")

    async def _generate_book_metadata(self, message: Manuscript, ctx: MessageContext) -> dict:
        """Generate comprehensive book metadata including title, author, and other details."""
        Console().print(Markdown("Generating book metadata..."))

        metadata_prompt = f"""
        Based on the following story synopsis and content, generate comprehensive metadata for a children's book:

        Synopsis: {message.synopsis or "N/A"}

        Story Content (first 1000 chars): {message.story[:1000]}...

        Please provide:
        1. A short, catchy book title (2-5 words max, fun and exciting for children ages 5-10)
        2. A brief subtitle if needed (optional, 1-4 words focusing on adventure/fun)
        3. Author name (use "FableFlow" as the author)
        4. Publisher name (use "FableFlow Publishing")
        5. A kid-friendly description (2-3 sentences written FOR children, using "you" and exciting language)
        6. Learning objectives (what children will discover, written as if talking to kids)
        7. Key educational themes (main concepts, kid-friendly language)
        8. Target age group confirmation
        9. Fun facts about the story (3-4 interesting things kids would love to know)
        10. Parent/educator summary (brief overview for adults)

        Format your response as:
        TITLE: [short, exciting title]
        SUBTITLE: [brief subtitle or "None"]
        AUTHOR: FableFlow
        PUBLISHER: FableFlow Publishing
        DESCRIPTION: [kid-friendly description using "you"]
        LEARNING_OBJECTIVES: [what you'll discover, written for kids]
        THEMES: [key concepts in kid language]
        AGE_GROUP: [target age range]
        FUN_FACTS: [3-4 cool facts kids would enjoy]
        PARENT_SUMMARY: [brief overview for adults]
        """

        metadata_result = await self._model_client.create(
            messages=[
                SystemMessage(
                    content="You are a children's book publishing expert. Generate professional, engaging metadata for educational children's books."
                ),
                UserMessage(content=metadata_prompt, source=self.id.key),
            ],
            cancellation_token=ctx.cancellation_token,
        )

        metadata_response = metadata_result.content
        return {
            "title": self._extract_from_response(metadata_response, "TITLE:", "Amazing Adventure"),
            "subtitle": self._extract_from_response(metadata_response, "SUBTITLE:", ""),
            "author": self._extract_from_response(metadata_response, "AUTHOR:", "FableFlow"),
            "publisher": self._extract_from_response(
                metadata_response, "PUBLISHER:", "FableFlow Publishing"
            ),
            "description": self._extract_from_response(
                metadata_response,
                "DESCRIPTION:",
                "Get ready for an amazing adventure full of surprises!",
            ),
            "learning_objectives": self._extract_from_response(
                metadata_response,
                "LEARNING_OBJECTIVES:",
                "You'll discover cool new things and have fun learning!",
            ),
            "themes": self._extract_from_response(
                metadata_response, "THEMES:", "Adventure, discovery, friendship"
            ),
            "age_group": self._extract_from_response(metadata_response, "AGE_GROUP:", "Ages 5-10"),
            "fun_facts": self._extract_from_response(
                metadata_response, "FUN_FACTS:", "This story has amazing pictures and sounds!"
            ),
            "parent_summary": self._extract_from_response(
                metadata_response,
                "PARENT_SUMMARY:",
                "An educational story that combines fun with learning.",
            ),
        }

    async def _generate_book_markdown(
        self, message: Manuscript, ctx: MessageContext, book_metadata: dict = None
    ) -> None:
        """Generate a book.md file using template with AI-generated content."""
        Console().print(Markdown("Generating enhanced book.md documentation..."))

        if not book_metadata:
            title_prompt = f"""
            Based on the following story synopsis and content, generate content for a children's book page:

            Synopsis: {message.synopsis or "N/A"}

            Story Content: {message.story}...

            Please provide:
            1. A short, exciting book title (2-5 words, perfect for kids ages 5-10)
            2. A kid-friendly description (written FOR children using "you" - make them excited!)
            3. Learning points (3-5 fun discoveries kids will make, written for children)
            4. Fun facts (3-4 cool things about the story)

            Format your response as:
            TITLE: [short exciting title]
            DESCRIPTION: [kid-friendly description with "you"]
            LEARNING_POINTS:
            - [discovery 1 for kids]
            - [discovery 2 for kids]
            - [discovery 3 for kids]
            FUN_FACTS:
            - [cool fact 1]
            - [cool fact 2]
            - [cool fact 3]
            """

            title_result = await self._model_client.create(
                messages=[
                    SystemMessage(
                        content="You are a children's book marketing expert. Generate engaging, age-appropriate content."
                    ),
                    UserMessage(content=title_prompt, source=self.id.key),
                ],
                cancellation_token=ctx.cancellation_token,
            )

            ai_response = title_result.content
            title = self._extract_from_response(ai_response, "TITLE:", "Story Adventure")
            description = self._extract_from_response(
                ai_response, "DESCRIPTION:", "An exciting story adventure!"
            )
            learning_points = self._extract_learning_points(ai_response)

            fun_facts = self._extract_learning_points(ai_response, "FUN_FACTS:")

            book_metadata = {
                "title": title,
                "description": description,
                "learning_points": learning_points,
                "fun_facts": fun_facts or "This story has amazing pictures and sounds!",
                "parent_summary": "An educational adventure story that combines entertainment with learning.",
                "age_group": "Ages 5-10",
                "themes": "Adventure, curiosity, friendship",
            }
        else:
            learning_objectives = book_metadata.get(
                "learning_objectives", "You'll discover amazing things!"
            )
            learning_points = f"\n\n* {learning_objectives}\n\n"

        # Use the template with enhanced metadata
        markdown_content = self._build_enhanced_template_content(book_metadata, learning_points)

        book_md_path = self.output_dir / "book.md"
        book_md_path.write_text(markdown_content, encoding="utf-8")

        logger.info(f"BookProducerAgent: Generated book.md file: {book_md_path}")
        Console().print(Markdown("✅ Created book.md with dynamic content"))

    def _insert_publication_info_UNUSED(self, content: str) -> str:
        """Insert publication information into the title page section."""
        publication_html = f"""
        <div class="publication-info">
            <p><strong>{config.book.publisher}</strong></p>
            <p>{config.book.edition}, {config.book.publication_year}</p>
            <br>
            <p>Based on original story by {config.book.draft_story_author}<br>
            Enhanced and modified by AI</p>
            <br>
            <p>All rights reserved</p>
            <br>
            <p><strong>ISBN: {config.book.isbn_pdf}</strong></p>
            <br>
            <p style="font-size: 11pt; font-style: italic;">
                No part of this publication may be reproduced, stored in a retrieval system,<br>
                or transmitted in any form or by any means without prior written permission.
            </p>
        </div>
        """

        title_patterns = [
            # Match div with title-page class (most likely)
            r'(<div[^>]*class="title-page"[^>]*>.*?</div>)',
            # Match div with title-page in class list
            r'(<div[^>]*class="[^"]*title-page[^"]*"[^>]*>.*?</div>)',
            # Match section with title-page class
            r'(<section[^>]*class="title-page"[^>]*>.*?</section>)',
            # Match div with id title-page
            r'(<div[^>]*id="title-page"[^>]*>.*?</div>)',
        ]

        inserted = False
        for pattern in title_patterns:
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                title_section = match.group(1)
                enhanced_title = title_section + publication_html
                content = content.replace(title_section, enhanced_title)
                inserted = True
                logger.info(
                    "BookProducerAgent: Successfully inserted publication info after title page"
                )
                break

        if not inserted:
            # Fallback 1: Look for title page heading and insert after it
            title_heading_patterns = [
                r'(<h[12][^>]*class="[^"]*title[^"]*"[^>]*>.*?</h[12]>)',
                r"(<h[12][^>]*>.*?Title.*?</h[12]>)",
            ]

            for pattern in title_heading_patterns:
                match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
                if match:
                    title_heading = match.group(1)
                    enhanced_heading = title_heading + publication_html
                    content = content.replace(title_heading, enhanced_heading)
                    inserted = True
                    logger.info("BookProducerAgent: Inserted publication info after title heading")
                    break

            if not inserted:
                # Final fallback: Insert after first major heading
                h1_match = re.search(r"(</h1>)", content, re.IGNORECASE)
                if h1_match:
                    content = content.replace(
                        h1_match.group(1), h1_match.group(1) + publication_html
                    )
                    logger.info(
                        "BookProducerAgent: Inserted publication info after first h1 (fallback)"
                    )
                else:
                    logger.warning(
                        "BookProducerAgent: Could not find suitable location for publication info"
                    )

        return content

    def _extract_from_response(self, response: str, marker: str, default: str) -> str:
        """Extract content after a marker from AI response."""
        lines = response.split("\n")
        for line in lines:
            if line.strip().startswith(marker):
                return line.replace(marker, "").strip()
        return default

    def _append_missing_back_matter(self, content: str, missing_sections: list) -> str:
        """Append missing back matter sections to ensure complete book structure."""
        additional_html = ""

        if "About the Author" in missing_sections:
            additional_html += f"""
    <div class="page-spread">
        <div class="page">
            <div class="about-author">
                <h2>About the Author</h2>
                <p class="story-text"><strong>{config.book.draft_story_author}</strong> is the original creator of this delightful children's story. With a passion for making learning accessible and enjoyable, Suneeta has crafted narratives that blend entertainment with education, helping young minds discover the wonders of science and everyday life.</p>
                <p class="story-text">This story has been enhanced and expanded using FableFlow, an innovative platform that transforms original stories into complete multimedia educational experiences. The combination of human creativity and artificial intelligence demonstrates the potential for technology to support and amplify educational storytelling.</p>
            </div>
        </div>
    </div>"""

        if "Index" in missing_sections:
            additional_html += """
    <div class="page-spread">
        <div class="page">
            <div class="index">
                <h2>Index</h2>
                <div class="index-entry"><span class="term">Adventure</span><span class="page-refs">1, 5, 12</span></div>
                <div class="index-entry"><span class="term">Bicycle</span><span class="page-refs">3, 8, 15</span></div>
                <div class="index-entry"><span class="term">Cassie</span><span class="page-refs">1, 3, 5, 8, 12, 15</span></div>
                <div class="index-entry"><span class="term">Curiosity</span><span class="page-refs">2, 6, 10</span></div>
                <div class="index-entry"><span class="term">Discovery</span><span class="page-refs">4, 9, 13</span></div>
                <div class="index-entry"><span class="term">Friendship</span><span class="page-refs">7, 11, 14</span></div>
                <div class="index-entry"><span class="term">Learning</span><span class="page-refs">2, 6, 10, 16</span></div>
                <div class="index-entry"><span class="term">Problem Solving</span><span class="page-refs">5, 9, 13</span></div>
            </div>
        </div>
    </div>"""

        if "Acknowledgments" in missing_sections:
            additional_html += """
    <div class="page-spread">
        <div class="page">
            <div class="acknowledgments">
                <h2>Acknowledgments</h2>
                <p class="story-text">This book would not exist without the countless curious children who ask "why?" with such persistence and joy. To every young scientist who has ever wondered about the world around them—this book celebrates you.</p>
                <p class="story-text">Deep gratitude to <span class="highlight">Suneeta Mall</span> for creating the original story that captures the essence of childhood curiosity and wonder. Your vision of making learning accessible and exciting for young readers continues to inspire.</p>
                <p class="story-text">Thank you to the parents, caregivers, and educators who take the time to answer children's questions and transform ordinary moments into extraordinary learning opportunities.</p>
                <p class="educational" style="margin-top: 0.2in; font-style: italic;">And finally, to every child who picks up this book: may you never stop asking "why?" The world is waiting for your discoveries.</p>
            </div>
        </div>
    </div>"""

        # Find the closing </div> and </body> tags and insert before them
        if content.endswith("</body>\n</html>"):
            content = content.replace("</body>\n</html>", f"{additional_html}\n</body>\n</html>")
        elif content.endswith("</div>\n\n</body>\n</html>"):
            content = content.replace(
                "</div>\n\n</body>\n</html>", f"{additional_html}\n</div>\n\n</body>\n</html>"
            )
        else:
            # Fallback: append before the last closing tags
            content = content.rstrip() + additional_html + "\n\n</body>\n</html>"

        return content

    def _format_as_markdown_list(self, text: str) -> str:
        """Format text as a proper markdown list with correct spacing."""
        if not text:
            return "\n\n* This story has amazing pictures and sounds!\n\n"

        # If text already contains bullet points, reformat them
        if "-" in text or "*" in text:
            lines = text.split("\n")
            formatted_lines = []
            for line in lines:
                line = line.strip()
                if line.startswith("-") or line.startswith("*"):
                    clean_line = line[1:].strip()
                    if clean_line:
                        formatted_lines.append(f"\n\n* {clean_line}")
                elif line:  # Non-empty line that doesn't start with bullet
                    formatted_lines.append(f"\n\n* {line}")

            if formatted_lines:
                return "".join(formatted_lines) + "\n\n"

        # If it's just plain text, treat as single item
        return f"\n\n* {text}\n\n"

    def _extract_learning_points(
        self, response: str, section_marker: str = "LEARNING_POINTS:"
    ) -> str:
        """Extract learning points from AI response."""
        lines = response.split("\n")
        points = []
        in_section = False

        for line in lines:
            if line.strip().startswith(section_marker):
                in_section = True
                continue
            elif in_section and line.strip().startswith("-"):
                # Format as proper markdown list item with proper spacing
                point_text = line.strip()[1:].strip()  # Remove the dash and extra spaces
                points.append(f"\n\n* {point_text}")
            elif in_section and line.strip() and not line.strip().startswith("-"):
                # End of section
                break

        if points:
            return "".join(points) + "\n\n"
        else:
            return "\n\n* Learn about friendship and adventure\n\n* Discover amazing new things\n\n* Build confidence and curiosity\n\n"

    def _build_enhanced_template_content(self, book_metadata: dict, learning_points: str) -> str:
        title = book_metadata.get("title", "Amazing Adventure")
        description = book_metadata.get(
            "description", "Get ready for an amazing adventure full of surprises!"
        )
        subtitle = book_metadata.get("subtitle", "")
        age_group = book_metadata.get("age_group", "Ages 5-10")
        themes = book_metadata.get("themes", "Adventure, discovery, friendship")
        fun_facts = book_metadata.get("fun_facts", "This story has amazing pictures and sounds!")
        parent_summary = book_metadata.get("parent_summary", "An educational adventure story.")

        epub_reader_id = re.sub(r"[^a-zA-Z0-9]+", "-", title.lower()).strip("-")
        if not epub_reader_id:
            epub_reader_id = "epub-reader-default"
        else:
            epub_reader_id = f"epub-reader-{epub_reader_id}"

        subtitle_display = f"\n## *{subtitle}*\n" if subtitle and subtitle != "None" else ""

        formatted_fun_facts = self._format_as_markdown_list(fun_facts)

        return f"""# 🌟 {title}

![FableFlow - Where Stories Come to Life](docs/assets/logo_horizontal.svg){{width=40%,align=center}}---
{subtitle_display}
**Perfect for {age_group}** 📚 **Created by {config.book.draft_story_author} with FableFlow** ✨

---

## 🎉 Hey Kids! Are You Ready for an Adventure?

{description}

![Story Adventure](image_0.png){{width=60%}}

## 🚀 What Will You Discover?

Get ready to explore and learn amazing things:{learning_points}

## 🎨 Cool Things About This Story:
{formatted_fun_facts}

![Story Friends](image_1.png){{width=60%}}

## 🌈 Adventures We'll Go On:
**{themes}** - and so much more!

---

## 📖 Choose Your Reading Adventure!

=== "📱 Read the Book Online"

    **Click and Read Right Here!**

    <div class="pdf-reader-container" style="width: 100%; position: relative; margin: 20px 0;">
        <div style="display: flex; justify-content: flex-end; margin-bottom: 10px; gap: 10px;">
            <button class="pdf-maximize-btn" style="display: inline-flex; align-items: center; gap: 5px; padding: 8px 16px; background-color: #2196F3; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; font-weight: 500; transition: background-color 0.3s;">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/>
                </svg>
                Maximize
            </button>
            <button class="pdf-minimize-btn" style="display: none; align-items: center; gap: 5px; padding: 8px 16px; background-color: #f44336; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; font-weight: 500; transition: background-color 0.3s;">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M8 3v3a2 2 0 0 1-2 2H3m18 0h-3a2 2 0 0 1-2-2V3m0 18v-3a2 2 0 0 1 2-2h3M3 16h3a2 2 0 0 1 2 2v3"/>
                </svg>
                Minimize
            </button>
        </div>
        <iframe src="../book.pdf" width="100%" height="800px" style="border: none; border-radius: 8px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);"></iframe>
    </div>

    🎯 **Perfect for:** Reading on tablets, computers, or phones

=== "📚 Interactive Book Reader"

    **Super Cool Book Reader!**

    <div id="{epub_reader_id}" class="epub-reader-container" data-epub-path="../book.epub" style="width: 100%; margin: 20px 0;">
        <div style="padding: 20px; text-align: center; background-color: #f8f9fa; border-radius: 8px;">
            <p>📖 Loading your awesome book...</p>
        </div>
    </div>

    **Cool Features:**


    * 📱 **Easy Navigation:** Use arrow keys or click buttons to turn pages

    * 📚 **Jump Around:** Skip to any chapter you want!

    * 🎯 **Fits Your Screen:** Works great on any device

    * 🖱️ **Interactive Fun:** Click and drag to explore

    *Having trouble? You can [📥 download the book](../book.epub) to read on your device!*

=== "💾 Take the Book With You"

    **Download and Keep Forever!**

    <div class="grid cards" markdown>

    -   📖 **PDF Book**

        ---

        Perfect for printing and reading anywhere!

        [📖 Get PDF Book](../book.pdf){{ .md-button .md-button--primary }}

    -   📚 **E-Reader Book**

        ---

        Read on Kindle, iPad, or any e-reader!

        [📚 Get E-Book](../book.epub){{ .md-button .md-button--primary }}

    </div>

---

## 🎧 Listen to the Story!

**Amazing Voice Reading Just for You!**

<audio controls style="width: 100%; height: 60px; border-radius: 8px; margin: 20px 0;">
  <source src="../narration.m4a" type="audio/mp4">
  Your browser does not support the audio element.
</audio>

🎵 **Perfect for:** Car trips, bedtime, or just relaxing while you listen!

---

## 🎬 Watch the Story Come Alive!

**5-Minute Video Preview - See the Magic!**

<video controls style="width: 100%; max-height: 600px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); margin: 20px 0;">
  <source src="../story_video.mp4" type="video/mp4">
  Your browser does not support the video element.
</video>

🌟 **What you'll see:** Animations, music, and your story characters moving around!

✨ **Special Note:** This is a short preview to get you excited about the full story!

---

## 🔬 For Amazing Young Scientists!

This story celebrates all the curious kids (like YOU!) who love to ask questions and discover new things!

Just like these famous scientists who were once curious kids too:


* **Sir Isaac Newton** 🍎 - He figured out why apples fall down (and helped us understand gravity!)

* **Albert Einstein** 🌟 - He discovered amazing secrets about space and time

* **Marie Curie** ⚗️ - She showed that being curious and never giving up helps you discover incredible things

* **YOU!** 🚀 - Every time you ask "why?" or "how?" you're being a scientist!

---

## 👨‍👩‍👧‍👦 For Parents & Educators

**Educational Value & Learning Outcomes**

{parent_summary}

**Key Learning Areas:**


* **Science Concepts:** {themes}

* **Critical Thinking:** Encourages questioning and exploration

* **Social Skills:** Promotes curiosity, empathy, and problem-solving

* **Digital Literacy:** Interactive multimedia experience

**Usage Suggestions:**


* **Bedtime Reading:** Use the audio narration for relaxing story time

* **Interactive Learning:** Explore the PDF/EPUB versions together

* **Discussion Starter:** Use the video preview to spark conversations

* **STEM Introduction:** Perfect gateway to science concepts

---

## 🤖 How This Amazing Book Was Made

**The Magic of AI Storytelling!**

This entire book was created using FableFlow - a super smart computer program that helps create amazing stories! From the exciting story to the beautiful pictures, the voice reading, and even the animations - everything was made with the help of artificial intelligence working together with human creativity.

**What makes this special:**


* 🎨 **AI-Generated Illustrations:** Every picture was created just for this story

* 🎵 **Custom Music & Narration:** Sounds made specifically for your adventure

* 📚 **Multiple Formats:** One story, many ways to enjoy it

* 🔬 **Educational Focus:** Learning disguised as pure fun!

---

**Want to create your own amazing stories?** [Discover FableFlow](https://github.com/suneeta-mall/fable-flow) 🚀
"""


@type_subscription(topic_type=config.agent_types.movie_director_type)
class MovieDirectorAgent(RoutedAgent):
    def __init__(
        self,
        model_client: ChatCompletionClient,
        output_dir: Path = Path(config.paths.output),
    ) -> None:
        super().__init__("Movie Director of the story.")
        self._system_message = SystemMessage(content=config.prompts.movie_director)
        self._model_client = EnhancedChatCompletionWrapper(model_client)
        self.output_dir = output_dir

    @message_handler
    async def handle_intermediate_text(self, message: Manuscript, ctx: MessageContext) -> None:
        output_file = self.output_dir / "movie_director.txt"

        if output_file.exists():
            logger.info(
                f"{self.id.type}: Skipping processing - output file already exists: {output_file}"
            )
            Console().print(
                Markdown(f"### {self.id.type}: Skipping - {output_file.name} already exists")
            )

            existing_content = output_file.read_text(encoding="utf-8")
            await self.publish_message(
                Manuscript(story=existing_content, synopsis=message.synopsis),
                topic_id=TopicId(config.agent_types.music_director, source=self.id.key),
            )
            await asyncio.sleep(3)
            await self.publish_message(
                Manuscript(story=existing_content, synopsis=message.synopsis),
                topic_id=TopicId(config.agent_types.animator, source=self.id.key),
            )
            return

        llm_result = await self._model_client.create(
            messages=[
                self._system_message,
                UserMessage(content=message.story, source=self.id.key),
            ],
            cancellation_token=ctx.cancellation_token,
        )

        Console().print(Markdown(f"### {self.id.type}: "))
        Console().print(Markdown(llm_result.content))
        output_file.write_text(llm_result.content, encoding="utf-8")
        logger.info(f"{self.id.type}: Generated and saved {output_file}")

        await self.publish_message(
            Manuscript(story=llm_result.content, synopsis=message.synopsis),
            topic_id=TopicId(config.agent_types.music_director, source=self.id.key),
        )
        await asyncio.sleep(3)
        await self.publish_message(
            Manuscript(story=llm_result.content, synopsis=message.synopsis),
            topic_id=TopicId(config.agent_types.animator, source=self.id.key),
        )


@type_subscription(topic_type=config.agent_types.music_director)
class MusicDirectorAgent(RoutedAgent):
    def __init__(
        self,
        model_client: ChatCompletionClient,
        output_dir: Path = Path(config.paths.output),
    ) -> None:
        super().__init__("Music Director for the video of the story.")
        self._system_message = SystemMessage(content=config.prompts.composer)
        self._model_client = EnhancedChatCompletionWrapper(model_client)
        self.output_dir = output_dir

    @message_handler
    async def handle_intermediate_text(self, message: Manuscript, ctx: MessageContext) -> None:
        output_file = self.output_dir / "music_director.txt"

        if output_file.exists():
            logger.info(
                f"{self.id.type}: Skipping processing - output file already exists: {output_file}"
            )
            Console().print(
                Markdown(f"### {self.id.type}: Skipping - {output_file.name} already exists")
            )

            # Read existing content and publish
            existing_content = output_file.read_text(encoding="utf-8")
            new_message = Manuscript(story=existing_content, synopsis=message.synopsis)
            await self.publish_message(
                new_message,
                topic_id=TopicId(config.agent_types.musician, source=self.id.key),
            )
            return

        llm_result = await self._model_client.create(
            messages=[
                self._system_message,
                UserMessage(content=message.story, source=self.id.key),
            ],
            cancellation_token=ctx.cancellation_token,
        )

        Console().print(Markdown(f"### {self.id.type}: "))
        Console().print(Markdown(llm_result.content))

        output_file.write_text(llm_result.content, encoding="utf-8")
        logger.info(f"{self.id.type}: Generated and saved {output_file}")

        new_message = Manuscript(story=llm_result.content, synopsis=message.synopsis)
        await self.publish_message(
            new_message,
            topic_id=TopicId(config.agent_types.musician, source=self.id.key),
        )


@type_subscription(topic_type=config.agent_types.musician)
class MusicianAgent(RoutedAgent):
    def __init__(
        self,
        output_dir: Path = Path(config.paths.output),
    ) -> None:
        super().__init__("The musician for the story.")
        self._music_model = EnhancedMusicModel()
        self.output_dir = output_dir

    @message_handler
    async def handle_intermediate_text(
        self,
        message: Manuscript,
        ctx: MessageContext,
    ) -> None:
        Console().print(Markdown(f"### {self.id.type}: "))
        music_segments = re.findall(r"<music>(.*?)</music>", message.story, re.DOTALL)

        if music_segments:
            for i, music_prompt in enumerate(music_segments):
                output_file = self.output_dir / f"music_{i}.mp3"

                if output_file.exists():
                    Console().print(Markdown(f"Skipping music_{i}.mp3 - already exists"))
                    continue

                music = await self._music_model.generate_music(music_prompt.strip())
                output_file.write_bytes(music)

                Console().print(Markdown(f"Generated music_{i}.mp3"))

        await self.write_fallback_music()

    async def write_fallback_music(self) -> None:
        fallback_file = self.output_dir / "music.mp3"
        if not fallback_file.exists():
            music = await self._music_model.generate_music("happy")
            fallback_file.write_bytes(music)
            Console().print(Markdown("Generated music.mp3"))
        else:
            Console().print(Markdown("Skipping music.mp3 - already exists"))


@type_subscription(topic_type=config.agent_types.animator)
class AnimatorAgent(RoutedAgent):
    def __init__(
        self,
        output_dir: Path = Path(config.paths.output),
    ) -> None:
        super().__init__("The animator for the story.")
        self._video_model = EnhancedVideoModel()
        self.output_dir = output_dir

    @message_handler
    async def handle_intermediate_text(
        self,
        message: Manuscript,
        ctx: MessageContext,
    ) -> None:
        message.clips = await self._video_model.generate_video(
            message.story, config.style.video, self.output_dir
        )
        await self.publish_message(
            message,
            topic_id=TopicId(config.agent_types.movie_producer, source=self.id.key),
        )


@type_subscription(topic_type=config.agent_types.movie_producer)
class MovieProducerAgent(RoutedAgent):
    def __init__(self, output_dir: Path = Path(config.paths.output)) -> None:
        super().__init__("A user agent that compiles.")
        self.output_dir = output_dir

    @message_handler
    async def handle_final_copy(self, message: Manuscript, ctx: MessageContext) -> None:
        Console().print(Markdown(f"### {self.id.type}: "))
        movie_fns = []

        fallback_music_fn = self.output_dir / "music.mp3"
        f_music = None
        if fallback_music_fn.exists():
            f_music = AudioFileClip(str(fallback_music_fn))
            logger.info(f"{self.id.type}: Found fallback music file: {fallback_music_fn}")

        for i, video in enumerate(message.clips):
            music_fn = str(self.output_dir / f"music_{i}.mp3")
            music = None
            if Path(music_fn).exists():
                music = AudioFileClip(music_fn)
                logger.info(f"{self.id.type}: Using indexed music file: {music_fn}")
            elif fallback_music_fn.exists():
                music = f_music
                logger.info(f"{self.id.type}: Using fallback music file: {fallback_music_fn}")

            if music is not None:
                # ImageSequenceClip doesn't have set_audio method, use with_audio instead
                video = video.with_audio(music)
            else:
                logger.warning(f"{self.id.type}: No music found for clip {i}")

            v_fn = self.output_dir / f"movie_{i}.mp4"
            video.write_videofile(str(v_fn), codec="libx264", audio_codec="aac", fps=24)
            movie_fns.append(v_fn)

        if movie_fns:
            vid_clips = [VideoFileClip(str(fn)) for fn in movie_fns]
            final_clip = concatenate_videoclips(vid_clips, method="compose")
            final_clip.write_videofile(
                str(self.output_dir / "story_video.mp4"), codec="libx264", audio_codec="aac", fps=24
            )
            # TODO unlink intermediate files
            # [fn.unlink() for fn in self.output_dir.glob("movie_*.mp4")]
            # [fn.unlink() for fn in self.output_dir.glob("music_*.mp3")]

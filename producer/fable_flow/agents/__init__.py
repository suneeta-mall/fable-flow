from __future__ import annotations

from fable_flow.agents.book_assembly import (
    ChapterStructureAgent,
    IllustrationGeneratorAgent,
    IllustrationPlacementAgent,
    create_book_content,
)
from fable_flow.agents.character_ref import CharacterReferenceAgent
from fable_flow.agents.enrichment import (
    BiographyAgent,
    ExperimentDesignerAgent,
    ReflectionGeneratorAgent,
    enrich_chapters,
)
from fable_flow.agents.movie_adaptation import (
    MovieAssemblerAgent,
    SceneExtractorAgent,
)
from fable_flow.agents.scene_production import SceneProductionCoordinator
from fable_flow.agents.story_development import (
    DraftStoryAgent,
    FinalProofAgent,
    StoryEditorAgent,
)

__all__ = [
    "BiographyAgent",
    "ChapterStructureAgent",
    "CharacterReferenceAgent",
    "DraftStoryAgent",
    "ExperimentDesignerAgent",
    "FinalProofAgent",
    "IllustrationGeneratorAgent",
    "IllustrationPlacementAgent",
    "MovieAssemblerAgent",
    "ReflectionGeneratorAgent",
    "SceneExtractorAgent",
    "SceneProductionCoordinator",
    "StoryEditorAgent",
    "create_book_content",
    "enrich_chapters",
]

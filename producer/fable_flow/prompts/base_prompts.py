from __future__ import annotations


class PromptBuilder:
    """Compose LLM prompts from labeled sections."""

    def __init__(self) -> None:
        self.sections: list[str] = []

    def add_role(self, role_description: str) -> PromptBuilder:
        self.sections.append(f"ROLE: {role_description}\n")
        return self

    def add_characters(self, character_descriptions: str) -> PromptBuilder:
        if character_descriptions:
            self.sections.append(character_descriptions)
        return self

    def add_custom_section(self, title: str, content: str) -> PromptBuilder:
        self.sections.append(f"{title.upper()}:\n{content}\n")
        return self

    def build(self) -> str:
        return "\n\n".join(self.sections)

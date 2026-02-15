from __future__ import annotations

from fable_flow.prompts import PromptBuilder


def test_prompt_builder_composes_sections():
    prompt = (
        PromptBuilder()
        .add_role("You are a children's book editor.")
        .add_custom_section("style guide", "Use simple sentences.")
        .build()
    )
    assert "ROLE: You are a children's book editor." in prompt
    assert "STYLE GUIDE:" in prompt
    assert "Use simple sentences." in prompt


def test_prompt_builder_ignores_empty_characters():
    prompt = PromptBuilder().add_role("Editor").add_characters("").build()
    assert "Editor" in prompt
    assert "CHARACTERS" not in prompt


def test_prompt_builder_chains_methods():
    builder = PromptBuilder()
    result = builder.add_role("X")
    assert result is builder

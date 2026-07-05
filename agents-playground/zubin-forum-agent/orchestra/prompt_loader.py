"""Load musician personas from Markdown prompt files."""

from pathlib import Path


PROMPTS_PATH = Path(__file__).resolve().parent.parent / "prompts"


def load_prompt(prompt_name: str) -> str:
    """Load one complete Markdown prompt document."""

    prompt_path = PROMPTS_PATH / f"{prompt_name.casefold()}.md"
    return prompt_path.read_text(encoding="utf-8").strip()


def load_persona(musician_name: str) -> str:
    """Load one musician's complete Markdown persona."""

    return load_prompt(musician_name)


def persona_role(persona: str) -> str:
    """Extract the plain-text Role section from a musician persona."""

    marker = "## Role"
    if marker not in persona:
        raise ValueError("Musician persona is missing its Role section.")

    role_section = persona.split(marker, 1)[1]
    return role_section.split("##", 1)[0].strip()

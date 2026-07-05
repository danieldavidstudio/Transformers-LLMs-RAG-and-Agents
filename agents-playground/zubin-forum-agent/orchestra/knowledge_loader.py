"""Load shared knowledge used by every Orchestra LLM prompt."""

from pathlib import Path


KNOWLEDGE_PATH = Path(__file__).resolve().parent.parent / "knowledge"


def load_rules() -> str:
    """Load the Orchestra's shared operating rules."""

    return (KNOWLEDGE_PATH / "rules.md").read_text(encoding="utf-8").strip()

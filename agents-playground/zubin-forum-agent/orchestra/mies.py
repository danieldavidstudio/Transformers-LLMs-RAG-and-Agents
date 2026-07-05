"""Mies, a future member of The Agentic Orchestra."""

from orchestra.musician import Musician
from orchestra.prompt_loader import load_persona, persona_role


class Mies(Musician):
    """Placeholder for a future musician."""

    def __init__(self) -> None:
        self.persona = load_persona("mies")
        super().__init__(name="Mies", role=persona_role(self.persona))

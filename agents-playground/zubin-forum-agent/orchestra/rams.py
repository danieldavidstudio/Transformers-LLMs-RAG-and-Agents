"""Rams, a future member of The Agentic Orchestra."""

from orchestra.musician import Musician
from orchestra.prompt_loader import load_persona, persona_role


class Rams(Musician):
    """Placeholder for a future musician."""

    def __init__(self) -> None:
        self.persona = load_persona("rams")
        super().__init__(name="Rams", role=persona_role(self.persona))

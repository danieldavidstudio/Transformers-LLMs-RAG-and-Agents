"""Rice, a future member of The Agentic Orchestra."""

from orchestra.musician import Musician
from orchestra.prompt_loader import load_persona, persona_role


class Rice(Musician):
    """Placeholder for a future musician."""

    def __init__(self) -> None:
        self.persona = load_persona("rice")
        super().__init__(name="Rice", role=persona_role(self.persona))

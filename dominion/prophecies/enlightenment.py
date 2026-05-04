"""Enlightenment Prophecy."""

from dataclasses import dataclass

from .base_prophecy import Prophecy
from .registry import register


@register
@dataclass
class Enlightenment(Prophecy):
    name: str = "Enlightenment"
    description: str = (
        "While active: Treasures are Actions for all purposes. If played in "
        "the Action phase, they produce +1 Card and +1 Action instead of "
        "their normal effects."
    )

    def on_activate(self, game_state) -> None:
        # The Action-phase substitution is handled at play time by the action
        # phase loop checking the prophecy. The "treasures are actions" rule
        # is exposed via Card.is_action which checks this prophecy.
        pass

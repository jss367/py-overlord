"""Way of the Camel — Exile a Gold from the Supply."""

from dominion.cards.registry import get_card
from .base_way import Way


class WayOfTheCamel(Way):
    def __init__(self):
        super().__init__("Way of the Camel")

    def apply(self, game_state, card) -> None:
        player = game_state.current_player
        if game_state.supply.get("Gold", 0) <= 0:
            return
        game_state.supply["Gold"] -= 1
        player.exile.append(get_card("Gold"))

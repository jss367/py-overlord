from dominion.cards.registry import get_card
from dominion.cards.base_card import Card
from .base_way import Way


class WayOfTheMouse(Way):
    """Play the set-aside card's effect instead of the played card's."""

    # Runs the set-aside card's on_play as its instruction proxy.
    uses_on_play_proxy = True

    def __init__(self, set_aside_card_name: str = "Village"):
        super().__init__("Way of the Mouse")
        self.set_aside_card = get_card(set_aside_card_name)

    def apply(self, game_state, card: Card) -> None:
        self.set_aside_card.on_play(game_state)
        # Note: Ally hooks for the originally-played ``card`` are fired by
        # the Action phase loop after ``way.apply`` returns.

from dominion.cards.base_card import CardCost
from .base_project import Project


class CardDraw(Project):
    """Example project that draws an extra card at the start of each turn."""

    def __init__(self):
        super().__init__("Card Draw", CardCost(coins=5))

    def on_turn_start(self, game_state, player) -> None:
        game_state.draw_cards(player, 1)

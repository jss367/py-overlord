from dominion.cards.base_card import CardCost
from .base_project import Project


class Sewers(Project):
    """When you trash a card, you may trash a card from your hand."""

    def __init__(self):
        super().__init__("Sewers", CardCost(coins=3))

    def on_trash(self, game_state, player, card) -> None:
        if not player.hand:
            return
        choice = player.ai.choose_card_to_trash(game_state, player.hand + [None])
        if choice:
            player.hand.remove(choice)
            game_state.trash_card(player, choice)

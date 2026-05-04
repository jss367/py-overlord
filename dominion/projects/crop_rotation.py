"""Crop Rotation: at the start of your turn, you may discard a Victory card
for +2 Cards."""

from dominion.cards.base_card import CardCost

from .base_project import Project


class CropRotation(Project):
    def __init__(self) -> None:
        super().__init__("Crop Rotation", CardCost(coins=6))

    def on_turn_start(self, game_state, player) -> None:
        victories = [
            c for c in player.hand if c.is_victory and not c.is_action
        ]
        if not victories:
            return
        # Always trade a junk Victory for cards.
        choice = min(victories, key=lambda c: (c.cost.coins, c.name))
        player.hand.remove(choice)
        game_state.discard_card(player, choice)
        game_state.draw_cards(player, 2)

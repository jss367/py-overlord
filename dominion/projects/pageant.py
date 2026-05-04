"""Pageant: at the end of your Buy phase, you may pay $1 for +1 Coffers."""

from dominion.cards.base_card import CardCost

from .base_project import Project


class Pageant(Project):
    def __init__(self) -> None:
        super().__init__("Pageant", CardCost(coins=3))

    def on_buy_phase_end(self, game_state, player) -> None:
        if player.coins < 1:
            return
        # Strict trade: $1 → +1 Coffers is essentially "carry $1 to next turn".
        # Always take the trade when possible.
        player.coins -= 1
        player.coin_tokens += 1

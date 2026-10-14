"""Guildhall: when you gain a Treasure, +1 Coffers."""

from dominion.cards.base_card import CardCost

from .base_project import Project


class Guildhall(Project):
    def __init__(self) -> None:
        super().__init__("Guildhall", CardCost(coins=5))

    def on_gain(self, game_state, player, card, *, treasure_at_gain=None) -> None:
        if treasure_at_gain is None:
            from dominion.cards.gain_decisions import gained_card_types
            treasure_at_gain = gained_card_types(game_state, player, card)[1]
        if treasure_at_gain:
            player.coin_tokens += 1

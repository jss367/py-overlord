"""Guildhall: when you gain a Treasure, +1 Coffers."""

from dominion.cards.base_card import CardCost

from .base_project import Project


class Guildhall(Project):
    def __init__(self) -> None:
        super().__init__("Guildhall", CardCost(coins=5))

    def on_gain(self, game_state, player, card) -> None:
        if card.is_treasure:
            player.coin_tokens += 1

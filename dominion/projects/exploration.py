"""Exploration: at the end of your Buy phase, if you didn't gain any Action
or Treasure cards in it, +1 Coffers and +1 Villager."""

from dominion.cards.base_card import CardCost

from .base_project import Project


class Exploration(Project):
    def __init__(self) -> None:
        super().__init__("Exploration", CardCost(coins=4))

    def on_buy_phase_end(self, game_state, player) -> None:
        if getattr(player, "gained_action_or_treasure_this_buy_phase", False):
            return
        player.coin_tokens += 1
        player.villagers += 1

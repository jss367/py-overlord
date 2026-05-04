"""Academy: when you gain an Action card, +1 Villager."""

from dominion.cards.base_card import CardCost

from .base_project import Project


class Academy(Project):
    def __init__(self) -> None:
        super().__init__("Academy", CardCost(coins=5))

    def on_gain(self, game_state, player, card) -> None:
        if card.is_action:
            player.villagers += 1

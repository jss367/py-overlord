from dominion.cards.base_card import CardCost
from .base_project import Project


class RoadNetwork(Project):
    def __init__(self):
        super().__init__("Road Network", CardCost(coins=5))

    def on_opponent_gain(self, game_state, owner, gained_card):
        if gained_card.is_victory:
            game_state.draw_cards(owner, 1)

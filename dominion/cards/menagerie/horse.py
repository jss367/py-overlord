"""Implementation of the Horse card from Menagerie."""

from ..base_card import Card, CardCost, CardStats, CardType


class Horse(Card):
    def __init__(self):
        super().__init__(
            name="Horse",
            cost=CardCost(coins=0),
            stats=CardStats(actions=1, cards=2),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        if self in player.in_play:
            player.in_play.remove(self)
        game_state.supply["Horse"] = game_state.supply.get("Horse", 0) + 1

"""Buried Treasure from the Plunder expansion."""

from ..base_card import Card, CardCost, CardStats, CardType


class BuriedTreasure(Card):
    """$5 Treasure-Duration: at start of next turn, +1 Buy and +$3."""

    def __init__(self):
        super().__init__(
            name="Buried Treasure",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.TREASURE, CardType.DURATION],
        )
        self.duration_persistent = True

    def play_effect(self, game_state):
        player = game_state.current_player
        player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        player.coins += 3
        player.buys += 1
        self.duration_persistent = False

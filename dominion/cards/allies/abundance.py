"""Implementation of the Abundance card from Allies."""

from ..base_card import Card, CardCost, CardStats, CardType


class Abundance(Card):
    """Treasure-Duration ($3): Now and at the start of your next turn:
    +1 Buy and +$1.
    """

    def __init__(self):
        super().__init__(
            name="Abundance",
            cost=CardCost(coins=3),
            stats=CardStats(coins=1, buys=1),
            types=[CardType.TREASURE, CardType.DURATION],
        )
        self.duration_persistent = True

    def play_effect(self, game_state):
        player = game_state.current_player
        player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        player.coins += 1
        player.buys += 1
        self.duration_persistent = False

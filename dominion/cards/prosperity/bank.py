from ..base_card import Card, CardCost, CardStats, CardType


class Bank(Card):
    """Simplified implementation of the Bank card."""

    def __init__(self):
        super().__init__(
            name="Bank",
            cost=CardCost(coins=7),
            stats=CardStats(),
            types=[CardType.TREASURE],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        treasures_in_play = sum(1 for c in player.in_play if c.is_treasure)
        player.coins += treasures_in_play

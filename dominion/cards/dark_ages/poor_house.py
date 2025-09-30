"""Implementation of the Poor House card."""

from ..base_card import Card, CardCost, CardStats, CardType


class PoorHouse(Card):
    def __init__(self):
        super().__init__(
            name="Poor House",
            cost=CardCost(coins=1),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        treasure_count = sum(1 for card in player.hand if card.is_treasure)
        coins = max(0, 4 - treasure_count)
        player.coins += coins

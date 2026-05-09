"""Philosopher's Stone - Treasure from Alchemy."""

from ..base_card import Card, CardCost, CardStats, CardType


class PhilosophersStone(Card):
    """Treasure ($3P): When you play this, +$1 per 5 cards (rounded down)
    in your deck and discard pile.
    """

    def __init__(self):
        super().__init__(
            name="Philosopher's Stone",
            cost=CardCost(coins=3, potions=1),
            stats=CardStats(),
            types=[CardType.TREASURE],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        total = len(player.deck) + len(player.discard)
        bonus = total // 5
        player.coins += bonus

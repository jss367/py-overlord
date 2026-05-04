"""Kiln - Treasure from Menagerie."""

from ..base_card import Card, CardCost, CardStats, CardType


class Kiln(Card):
    """$2. The next time you play a Card this turn, gain a copy of it."""

    def __init__(self):
        super().__init__(
            name="Kiln",
            cost=CardCost(coins=5),
            stats=CardStats(coins=2),
            types=[CardType.TREASURE],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        # Mark the next card play to be copied
        player.kiln_pending = getattr(player, "kiln_pending", 0) + 1

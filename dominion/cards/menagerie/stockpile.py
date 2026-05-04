"""Stockpile - Treasure from Menagerie."""

from ..base_card import Card, CardCost, CardStats, CardType


class Stockpile(Card):
    """+$3 +1 Buy. When you play this, exile it."""

    def __init__(self):
        super().__init__(
            name="Stockpile",
            cost=CardCost(coins=3),
            stats=CardStats(coins=3, buys=1),
            types=[CardType.TREASURE],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        # Exile the card from in_play
        if self in player.in_play:
            player.in_play.remove(self)
            player.exile.append(self)

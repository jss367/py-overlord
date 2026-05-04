"""Patron: Action ($4). +1 Villager. +$2.

(Worth 0 VP — implicit since the card has no VP stats.)

When something causes you to reveal this (from your hand, deck, or
discard), +1 Coffers.
"""

from ..base_card import Card, CardCost, CardStats, CardType


class Patron(Card):
    def __init__(self) -> None:
        super().__init__(
            name="Patron",
            cost=CardCost(coins=4),
            stats=CardStats(coins=2),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        game_state.current_player.villagers += 1

    def on_reveal(self, game_state, player) -> None:
        """Hook used by code paths that explicitly reveal cards."""
        player.coin_tokens += 1

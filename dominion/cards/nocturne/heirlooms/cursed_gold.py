"""Cursed Gold — Pooka's Heirloom."""

from ...base_card import Card, CardCost, CardStats, CardType


class CursedGold(Card):
    """$3 Treasure-Heirloom: when you play this, gain a Curse."""

    def __init__(self):
        super().__init__(
            name="Cursed Gold",
            cost=CardCost(coins=4),
            stats=CardStats(coins=3),
            types=[CardType.TREASURE, CardType.HEIRLOOM],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        game_state.give_curse_to_player(player)

    def starting_supply(self, game_state) -> int:  # pragma: no cover
        return 0

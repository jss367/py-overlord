"""Vineyard - Victory from Alchemy."""

from ..base_card import Card, CardCost, CardStats, CardType


class Vineyard(Card):
    """Victory (P): Worth 1 VP per 3 Action cards in your deck (rounded down).

    "Your deck" in Dominion VP scoring means every card the player owns
    (deck, discard, hand, in-play, set-aside / mat / exile / etc.).
    """

    def __init__(self):
        super().__init__(
            name="Vineyard",
            cost=CardCost(coins=0, potions=1),
            stats=CardStats(),
            types=[CardType.VICTORY],
        )

    def get_victory_points(self, player) -> int:
        action_count = sum(1 for c in player.all_cards() if c.is_action)
        return action_count // 3

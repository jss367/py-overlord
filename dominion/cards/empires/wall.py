"""Implementation of Wall.

Wall is officially a Landmark in Empires: ``When scoring, -1 VP per card
you have over 15.`` This codebase has no Landmark infrastructure, so Wall
is modeled as a $4 Victory kingdom card. To preserve the once-applied
nature of the Landmark penalty, only the first Wall in a player's deck
contributes the negative VP — owning extra copies does not multiply the
penalty.
"""

from ..base_card import Card, CardCost, CardStats, CardType


class Wall(Card):
    def __init__(self):
        super().__init__(
            name="Wall",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.VICTORY],
        )

    def get_victory_points(self, player) -> int:
        all_cards = player.all_cards()
        for card in all_cards:
            if card.name == "Wall":
                if card is not self:
                    return 0
                break
        excess = max(0, len(all_cards) - 15)
        return -excess

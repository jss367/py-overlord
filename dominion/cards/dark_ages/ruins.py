from ..base_card import Card, CardCost, CardStats, CardType


class Ruins(Card):
    """Simplified Ruins placeholder."""

    def __init__(self):
        super().__init__(
            name="Ruins",
            cost=CardCost(coins=0),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def may_be_bought(self, game_state) -> bool:  # pragma: no cover - not in supply
        return False

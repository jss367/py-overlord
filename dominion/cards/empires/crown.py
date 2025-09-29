from ..base_card import Card, CardCost, CardStats, CardType


class Crown(Card):
    """Simplified Crown that boosts economy in either phase."""

    def __init__(self):
        super().__init__(
            name="Crown",
            cost=CardCost(coins=5),
            stats=CardStats(actions=1, coins=1),
            types=[CardType.ACTION, CardType.TREASURE],
        )

    def play_effect(self, game_state):
        # In this simplified model Crown just grants its printed bonuses.
        pass

from ..base_card import Card, CardCost, CardStats, CardType


class Fairgrounds(Card):
    """Victory card worth points for deck diversity."""

    def __init__(self):
        super().__init__(
            name="Fairgrounds",
            cost=CardCost(coins=6),
            stats=CardStats(),
            types=[CardType.VICTORY],
        )

    def get_victory_points(self, player) -> int:
        unique_names = {card.name for card in player.all_cards()}
        return (len(unique_names) // 5) * 2

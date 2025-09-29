from ..base_card import Card, CardCost, CardStats, CardType


class SilkRoad(Card):
    def __init__(self):
        super().__init__(
            name="Silk Road",
            cost=CardCost(coins=4),
            stats=CardStats(vp=0),
            types=[CardType.VICTORY],
        )

    def get_victory_points(self, player) -> int:
        victory_cards = sum(1 for card in player.all_cards() if card.is_victory)
        return victory_cards // 4

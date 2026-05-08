from ..base_card import Card, CardCost, CardStats, CardType


class Farrier(Card):
    """+1 Card / +1 Action / +1 Buy. Overpay: at the end of this turn,
    +1 Card per $1 overpaid."""

    def __init__(self):
        super().__init__(
            name="Farrier",
            cost=CardCost(coins=3),
            stats=CardStats(cards=1, actions=1, buys=1),
            types=[CardType.ACTION],
        )

    def may_overpay(self, game_state) -> bool:
        return True

    def on_overpay(self, game_state, player, amount: int) -> None:
        if amount <= 0:
            return
        player.farrier_pending_draw += amount

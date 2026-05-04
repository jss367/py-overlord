from ..base_card import Card, CardCost, CardStats, CardType


class Masterpiece(Card):
    """Guilds overpay Treasure — each $1 overpaid gains a Silver."""

    def __init__(self):
        super().__init__(
            name="Masterpiece",
            cost=CardCost(coins=3),
            stats=CardStats(coins=1),
            types=[CardType.TREASURE],
        )

    def may_overpay(self, game_state) -> bool:
        return True

    def on_overpay(self, game_state, player, amount: int) -> None:
        if amount <= 0:
            return
        from ..registry import get_card

        for _ in range(amount):
            if game_state.supply.get("Silver", 0) <= 0:
                break
            game_state.supply["Silver"] -= 1
            game_state.gain_card(player, get_card("Silver"))

"""Port (Adventures) — $4 Action."""

from ..base_card import Card, CardCost, CardStats, CardType


class Port(Card):
    def __init__(self):
        super().__init__(
            name="Port",
            cost=CardCost(coins=4),
            stats=CardStats(cards=1, actions=2),
            types=[CardType.ACTION],
        )

    def starting_supply(self, game_state) -> int:
        return 12

    def on_buy(self, game_state):
        # When you buy this, also gain a second Port.
        from ..registry import get_card

        player = game_state.current_player
        if game_state.supply.get("Port", 0) <= 0:
            return
        game_state.supply["Port"] -= 1
        game_state.gain_card(player, get_card("Port"))

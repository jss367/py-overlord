from ..base_card import Card, CardCost, CardStats, CardType


class Skulk(Card):
    def __init__(self):
        super().__init__(
            name="Skulk",
            cost=CardCost(coins=4),
            stats=CardStats(buys=1, coins=2),
            types=[CardType.ACTION],
        )

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)
        if game_state.supply.get("Gold", 0) > 0:
            from ..registry import get_card

            game_state.supply["Gold"] -= 1
            gold = get_card("Gold")
            game_state.gain_card(player, gold)

from ..base_card import Card, CardCost, CardStats, CardType


class Cache(Card):
    def __init__(self):
        super().__init__(
            name="Cache",
            cost=CardCost(coins=5),
            stats=CardStats(coins=3),
            types=[CardType.TREASURE],
        )

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)

        from ..registry import get_card

        for _ in range(2):
            if game_state.supply.get("Copper", 0) <= 0:
                break
            game_state.supply["Copper"] -= 1
            game_state.gain_card(player, get_card("Copper"))

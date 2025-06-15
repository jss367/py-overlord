from ..base_card import Card, CardCost, CardStats, CardType


class Hoard(Card):
    def __init__(self):
        super().__init__(
            name="Hoard",
            cost=CardCost(coins=6),
            stats=CardStats(coins=2),
            types=[CardType.TREASURE],
        )

    def on_buy(self, game_state):
        from ..registry import get_card

        if game_state.supply.get("Gold", 0) > 0:
            game_state.supply["Gold"] -= 1
            gold = get_card("Gold")
            player = game_state.current_player
            game_state.gain_card(player, gold)

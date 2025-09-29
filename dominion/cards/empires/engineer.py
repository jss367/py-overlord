from ..base_card import Card, CardCost, CardStats, CardType


class Engineer(Card):
    def __init__(self):
        super().__init__(
            name="Engineer",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        from ..registry import get_card

        affordable = [
            name
            for name, count in game_state.supply.items()
            if count > 0 and get_card(name).cost.coins <= 4
        ]
        if not affordable:
            return
        gain_name = affordable[0]
        gain = get_card(gain_name)
        game_state.supply[gain_name] -= 1
        game_state.gain_card(player, gain)

from ..base_card import Card, CardCost, CardStats, CardType


class Talisman(Card):
    def __init__(self):
        super().__init__(
            name="Talisman",
            cost=CardCost(coins=4),
            stats=CardStats(coins=1, buys=1),
            types=[CardType.TREASURE],
        )

    def on_buy(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        affordable = [
            name
            for name, count in game_state.supply.items()
            if count > 0 and get_card(name).cost.coins <= 4
        ]
        if not affordable:
            return

        gain_card = player.ai.choose_buy(game_state, [get_card(n) for n in affordable])
        if gain_card is None:
            gain_card = get_card(affordable[0])

        game_state.supply[gain_card.name] -= 1
        player.discard.append(gain_card)
        gain_card.on_gain(game_state, player)

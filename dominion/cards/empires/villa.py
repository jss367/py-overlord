from ..base_card import Card, CardCost, CardStats, CardType


class Villa(Card):
    def __init__(self):
        super().__init__(
            name="Villa",
            cost=CardCost(coins=4),
            stats=CardStats(actions=2, coins=2, buys=1),
            types=[CardType.ACTION],
        )

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)
        if self in player.discard:
            player.discard.remove(self)
            player.hand.append(self)
        player.actions += 2
        game_state.phase = "action"

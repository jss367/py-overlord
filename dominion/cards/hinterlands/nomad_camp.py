from ..base_card import Card, CardCost, CardStats, CardType


class NomadCamp(Card):
    def __init__(self):
        super().__init__(
            name="Nomad Camp",
            cost=CardCost(coins=4),
            stats=CardStats(coins=2, buys=1),
            types=[CardType.ACTION],
        )

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)

        if self in player.discard:
            player.discard.remove(self)
            player.deck.insert(0, self)

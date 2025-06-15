from ..base_card import Card, CardCost, CardStats, CardType


class RoyalSeal(Card):
    def __init__(self):
        super().__init__(
            name="Royal Seal",
            cost=CardCost(coins=5),
            stats=CardStats(coins=2),
            types=[CardType.TREASURE],
        )

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)
        if self in player.discard:
            player.discard.remove(self)
            player.deck.append(self)

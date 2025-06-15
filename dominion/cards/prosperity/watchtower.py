from ..base_card import Card, CardCost, CardStats, CardType


class Watchtower(Card):
    def __init__(self):
        super().__init__(
            name="Watchtower",
            cost=CardCost(coins=3),
            stats=CardStats(cards=2),
            types=[CardType.ACTION, CardType.REACTION],
        )

    def play_effect(self, game_state):
        # TODO: discard cards for coins
        pass

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)
        # TODO: may place gained card on deck or trash it
        pass

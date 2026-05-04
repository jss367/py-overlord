"""Lost City (Adventures) — $5 Action."""

from ..base_card import Card, CardCost, CardStats, CardType


class LostCity(Card):
    def __init__(self):
        super().__init__(
            name="Lost City",
            cost=CardCost(coins=5),
            stats=CardStats(actions=2, cards=2),
            types=[CardType.ACTION],
        )

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)
        # When you gain this, each other player draws a card.
        for other in game_state.players:
            if other is player:
                continue
            game_state.draw_cards(other, 1)

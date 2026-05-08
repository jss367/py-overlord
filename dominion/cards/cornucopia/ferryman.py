from ..base_card import Card, CardCost, CardStats, CardType


class Ferryman(Card):
    """+2 Cards / +1 Action. Setup: add an extra Kingdom pile costing $3 to
    the Supply. When you gain this, also gain a card from that pile."""

    def __init__(self):
        super().__init__(
            name="Ferryman",
            cost=CardCost(coins=4),
            stats=CardStats(cards=2, actions=1),
            types=[CardType.ACTION],
        )

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)
        from ..registry import get_card

        chosen = getattr(game_state, "ferryman_card_name", "")
        if not chosen:
            return
        if game_state.supply.get(chosen, 0) <= 0:
            return
        game_state.supply[chosen] -= 1
        game_state.gain_card(player, get_card(chosen))

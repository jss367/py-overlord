from ..base_card import Card, CardCost, CardStats, CardType


class Ferryman(Card):
    """+2 Cards / +1 Action. Gain a card costing exactly $3 (the same one
    each game, randomly chosen at game start)."""

    def __init__(self):
        super().__init__(
            name="Ferryman",
            cost=CardCost(coins=4),
            stats=CardStats(cards=2, actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        chosen = getattr(game_state, "ferryman_card_name", "")
        if not chosen:
            return
        if game_state.supply.get(chosen, 0) <= 0:
            return
        game_state.supply[chosen] -= 1
        game_state.gain_card(game_state.current_player, get_card(chosen))

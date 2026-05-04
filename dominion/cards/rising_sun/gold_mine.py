from ..base_card import Card, CardCost, CardStats, CardType


class GoldMine(Card):
    """Action-Shadow ($5): +1 Card, +1 Action, +1 Buy.
    You may gain a Gold; if you do, take 4 Debt.
    """

    def __init__(self):
        super().__init__(
            name="Gold Mine",
            cost=CardCost(coins=5),
            stats=CardStats(cards=1, actions=1, buys=1),
            types=[CardType.ACTION, CardType.SHADOW],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player

        if game_state.supply.get("Gold", 0) <= 0:
            return
        if not player.ai.should_take_gold_mine_gold(game_state, player):
            return

        game_state.supply["Gold"] -= 1
        game_state.gain_card(player, get_card("Gold"))
        player.debt += 4

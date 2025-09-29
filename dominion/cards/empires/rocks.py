from ..base_card import Card, CardCost, CardStats, CardType
from ..split_pile import BottomSplitPileCard


class Rocks(BottomSplitPileCard):
    partner_card_name = "Catapult"

    def __init__(self):
        super().__init__(
            name="Rocks",
            cost=CardCost(coins=4),
            stats=CardStats(coins=1, vp=1),
            types=[CardType.TREASURE, CardType.VICTORY],
        )

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)
        if game_state.supply.get("Silver", 0) > 0:
            game_state.supply["Silver"] -= 1
            from ..registry import get_card

            silver = get_card("Silver")
            game_state.gain_card(player, silver)

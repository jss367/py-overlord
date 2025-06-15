from ..base_card import CardCost, CardStats, CardType
from ..split_pile import BottomSplitPileCard


class Emporium(BottomSplitPileCard):
    partner_card_name = "Patrician"
    def __init__(self):
        super().__init__(
            name="Emporium",
            cost=CardCost(coins=5),
            stats=CardStats(actions=2, cards=2, vp=2),
            types=[CardType.ACTION, CardType.VICTORY],
        )


    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)
        if any(card.name == "Patrician" for card in player.in_play):
            player.vp_tokens += 2

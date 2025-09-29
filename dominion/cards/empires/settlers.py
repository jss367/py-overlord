from ..base_card import CardCost, CardStats, CardType
from ..split_pile import TopSplitPileCard
from ..treasures import Copper


class Settlers(TopSplitPileCard):
    partner_card_name = "Bustling Village"

    def __init__(self):
        super().__init__(
            name="Settlers",
            cost=CardCost(coins=2),
            stats=CardStats(cards=1, actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        for idx, card in enumerate(player.discard):
            if isinstance(card, Copper):
                player.hand.append(player.discard.pop(idx))
                break

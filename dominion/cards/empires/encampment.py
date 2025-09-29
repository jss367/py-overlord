from ..base_card import CardCost, CardStats, CardType
from ..split_pile import TopSplitPileCard


class Encampment(TopSplitPileCard):
    partner_card_name = "Plunder"

    def __init__(self):
        super().__init__(
            name="Encampment",
            cost=CardCost(coins=2),
            stats=CardStats(actions=2, coins=2),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        keep = any(card.name in {"Gold", "Plunder"} for card in player.hand)
        if not keep and self in player.in_play:
            player.in_play.remove(self)
            game_state.supply[self.name] = game_state.supply.get(self.name, 0) + 1

from ..base_card import Card, CardCost, CardStats, CardType
from ..split_pile import BottomSplitPileCard


class Avanto(BottomSplitPileCard):
    partner_card_name = "Sauna"

    def __init__(self):
        super().__init__(
            name="Avanto",
            cost=CardCost(coins=5),
            stats=CardStats(cards=3),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        saunas = [card for card in player.hand if card.name == "Sauna"]
        if not saunas:
            return
        if not player.ai.should_play_sauna_from_avanto(game_state, player):
            return
        target = saunas[0]
        if not game_state.move_card_from_hand_to_play(player, target):
            return
        target.on_play(game_state)

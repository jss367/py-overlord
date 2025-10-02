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
        chosen = player.ai.should_play_sauna_with_avanto(game_state, player, list(saunas))
        if not chosen:
            return
        if chosen is True:
            sauna = saunas[0]
        elif chosen in saunas:
            sauna = chosen
        else:
            sauna = saunas[0]
        if sauna not in player.hand:
            return
        player.hand.remove(sauna)
        player.in_play.append(sauna)
        sauna.on_play(game_state)

from ..base_card import Card, CardCost, CardStats, CardType
from ..split_pile import TopSplitPileCard


class Sauna(TopSplitPileCard):
    partner_card_name = "Avanto"

    def __init__(self):
        super().__init__(
            name="Sauna",
            cost=CardCost(coins=4),
            stats=CardStats(cards=1, actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        avantos = [card for card in player.hand if card.name == "Avanto"]
        if not avantos:
            return

        chosen = player.ai.should_play_avanto_with_sauna(game_state, player, list(avantos))
        if not chosen:
            return

        if chosen is True:
            avanto = avantos[0]
        elif chosen in avantos:
            avanto = chosen
        else:
            avanto = avantos[0]
        if avanto not in player.hand:
            return
        player.hand.remove(avanto)
        player.in_play.append(avanto)
        avanto.on_play(game_state)

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)
        if game_state.supply.get("Silver", 0) <= 0:
            return
        if not player.ai.should_gain_silver_with_sauna(game_state, player):
            return
        from ..registry import get_card

        game_state.supply["Silver"] -= 1
        game_state.gain_card(player, get_card("Silver"))

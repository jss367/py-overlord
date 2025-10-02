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
        if not player.ai.should_play_avanto_from_sauna(game_state, player):
            return
        target = avantos[0]
        player.hand.remove(target)
        player.in_play.append(target)
        target.on_play(game_state)

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)
        if not player.hand:
            return
        to_trash = player.ai.choose_card_to_trash(game_state, list(player.hand) + [None])
        if to_trash and to_trash in player.hand:
            player.hand.remove(to_trash)
            game_state.trash_card(player, to_trash)

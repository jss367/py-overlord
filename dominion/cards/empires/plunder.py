from ..base_card import Card, CardCost, CardStats, CardType
from ..split_pile import BottomSplitPileCard


class Plunder(BottomSplitPileCard):
    partner_card_name = "Encampment"

    def __init__(self):
        super().__init__(
            name="Plunder",
            cost=CardCost(coins=5),
            stats=CardStats(coins=2, buys=1),
            types=[CardType.TREASURE],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        if game_state.supply.get("Gold", 0) <= 0:
            return

        game_state.supply["Gold"] -= 1

        from ..registry import get_card

        gold = get_card("Gold")
        game_state.gain_card(player, gold, to_deck=True)

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)
        if game_state.supply.get("Gold", 0) > 0:
            game_state.supply["Gold"] -= 1
            from ..registry import get_card

            gold = get_card("Gold")
            game_state.gain_card(player, gold)

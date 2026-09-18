from ..base_card import CardCost, CardStats, CardType
from ..split_pile import BottomSplitPileCard


class Rocks(BottomSplitPileCard):
    """$4 Treasure: $1; on gain or trash gain a Silver to deck or hand."""

    partner_card_name = "Catapult"

    def __init__(self):
        super().__init__(
            name="Rocks",
            cost=CardCost(coins=4),
            stats=CardStats(coins=1),
            types=[CardType.TREASURE],
        )

    def _gain_silver(self, game_state, player):
        if game_state.supply.get("Silver", 0) > 0:
            game_state.supply["Silver"] -= 1
            from ..registry import get_card

            # The simulator splits the rules' Buy phase into treasure and buy.
            own_buy_phase = (game_state.turn_player is player
                             and game_state.phase in {"treasure", "buy"})
            game_state.gain_card(player, get_card("Silver"),
                                 to_deck=own_buy_phase, to_hand=not own_buy_phase)

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)
        self._gain_silver(game_state, player)

    def on_trash(self, game_state, player):
        super().on_trash(game_state, player)
        self._gain_silver(game_state, player)

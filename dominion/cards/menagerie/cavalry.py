"""Cavalry - Action from Menagerie."""

from ..base_card import Card, CardCost, CardStats, CardType


class Cavalry(Card):
    """Gain 2 Horses. When you gain this, +2 Cards +1 Buy and if it's your
    Buy phase, return to Action phase.
    """

    def __init__(self):
        super().__init__(
            name="Cavalry",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        for _ in range(2):
            if game_state.supply.get("Horse", 0) <= 0:
                break
            game_state.supply["Horse"] -= 1
            game_state.gain_card(player, get_card("Horse"))

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)

        # +2 Cards, +1 Buy
        game_state.draw_cards(player, 2)
        player.buys += 1

        # If we're in the Buy phase, return to Action phase (once per turn).
        # The card text only specifies returning to the Action phase; it does
        # not grant extra Actions, so leave ``player.actions`` untouched.
        if game_state.phase == "buy" and not getattr(player, "cavalry_returned_this_turn", False):
            player.cavalry_returned_this_turn = True
            game_state.phase = "action"

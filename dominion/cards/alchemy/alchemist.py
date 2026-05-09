"""Alchemist - Action from Alchemy."""

from ..base_card import Card, CardCost, CardStats, CardType


class Alchemist(Card):
    """Action ($3P): +2 Cards, +1 Action.

    At the start of Clean-up, if you have a Potion in play, you may put this
    onto your deck. We hook ``on_buy_phase_end`` (which fires before cleanup
    discards in-play cards) and topdeck Alchemist there, mirroring how
    Treasury handles its own end-of-buy-phase topdeck.
    """

    def __init__(self):
        super().__init__(
            name="Alchemist",
            cost=CardCost(coins=3, potions=1),
            stats=CardStats(actions=1, cards=2),
            types=[CardType.ACTION],
        )

    def on_buy_phase_end(self, game_state):
        player = game_state.current_player
        if not any(c.name == "Potion" for c in player.in_play):
            return
        if self not in player.in_play:
            return
        if not player.ai.should_topdeck_alchemist(game_state, player):
            return
        player.in_play.remove(self)
        player.deck.append(self)
        game_state.log_callback(
            ("action", player.ai.name, "topdecks Alchemist", {})
        )

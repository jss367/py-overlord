"""Implementation of Coppersmith (1E)."""

from ..base_card import Card, CardCost, CardStats, CardType


class Coppersmith(Card):
    """+1 Action. Each Copper you play this turn produces an extra $1.

    Note: applies to Coppers played AFTER Coppersmith. (The official rule
    is "this turn", but in practice the typical line is to play
    Coppersmith first and then Coppers; treasures are played after
    actions.) The bonus stacks: each Coppersmith adds +$1 per Copper.
    """

    def __init__(self):
        super().__init__(
            name="Coppersmith",
            cost=CardCost(coins=4),
            stats=CardStats(actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        player.coppersmiths_played = getattr(player, "coppersmiths_played", 0) + 1

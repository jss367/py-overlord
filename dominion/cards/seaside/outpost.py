from ..base_card import Card, CardCost, CardStats, CardType


class Outpost(Card):
    """Action-Duration ($5): If the previous turn wasn't yours, take an extra turn
    after this one, and only draw 3 cards for it.
    """

    def __init__(self):
        super().__init__(
            name="Outpost",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.DURATION],
        )
        self.duration_persistent = True

    def play_effect(self, game_state):
        player = game_state.current_player

        # Outposts can't chain — if this turn is already an extra turn from a
        # previous Outpost, don't schedule another. The card still enters the
        # duration zone so cleanup discards it correctly next turn.
        if not getattr(player, "outpost_taken_last_turn", False):
            player.outpost_pending = True

        player.duration.append(self)

    def on_duration(self, game_state):
        # Outpost has no other duration effect; it just gets discarded.
        self.duration_persistent = False

from ..base_card import Card, CardCost, CardStats, CardType


class Crew(Card):
    """Plunder $5 Action-Duration: +3 Cards. At start of next turn, top-deck this."""

    def __init__(self):
        super().__init__(
            name="Crew",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.DURATION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        game_state.draw_cards(player, 3)
        # Stay in play until the start-of-next-turn duration trigger fires.
        self.duration_persistent = True
        player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        # Move Crew from duration to top of deck. Mark as persistent so the
        # engine's post-on_duration cleanup does not also try to discard it.
        if self in player.duration:
            player.duration.remove(self)
        player.deck.append(self)
        self.duration_persistent = True

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
        self.duration_persistent = False
        # Guard against duplicate listings when Crew is replayed in the same
        # turn (Flagship, Throne Room, etc. operate on the same instance).
        # Each replay still draws +3 above, but the duration list may only
        # carry the card once or on_duration would top-deck it multiple times.
        if self not in player.duration:
            player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        # This effect finishes now. If Crew already left play, it cannot move
        # itself again; pending instructions do not restore physical ownership.
        self.duration_persistent = False
        if self not in player.in_play and self not in player.duration:
            return
        if self in player.duration:
            player.duration.remove(self)
        if self in player.in_play:
            player.in_play.remove(self)
        player.deck.append(self)

"""Landing Party from the Plunder expansion."""

from ..base_card import Card, CardCost, CardStats, CardType


class LandingParty(Card):
    """$4 Action-Duration: +2 Cards, +1 Action. The next time you discard this
    from play, put it on top of your deck.
    """

    def __init__(self):
        super().__init__(
            name="Landing Party",
            cost=CardCost(coins=4),
            stats=CardStats(cards=2, actions=1),
            types=[CardType.ACTION, CardType.DURATION],
        )
        self.duration_persistent = True

    def play_effect(self, game_state):
        player = game_state.current_player
        player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        # Move from duration/in_play onto top of deck. Suppress default discard.
        if self in player.duration:
            player.duration.remove(self)
        if self in player.in_play:
            player.in_play.remove(self)
        player.deck.append(self)
        self.duration_persistent = True

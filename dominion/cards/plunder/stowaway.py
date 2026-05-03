"""Stowaway from the Plunder expansion."""

from ..base_card import Card, CardCost, CardStats, CardType


class Stowaway(Card):
    """$3 Action-Duration-Reaction: Now and at start of next turn, +2 Cards, +1 Action.

    When another player plays an Attack, you may set this aside from your hand
    to play it before resolving the attack. Reaction tracking is left to AIs
    that opt in via ``stowaway_react_to_attack``.
    """

    def __init__(self):
        super().__init__(
            name="Stowaway",
            cost=CardCost(coins=3),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.DURATION, CardType.REACTION],
        )
        self.duration_persistent = True

    def play_effect(self, game_state):
        player = game_state.current_player
        game_state.draw_cards(player, 2)
        player.actions += 1
        player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        game_state.draw_cards(player, 2)
        player.actions += 1
        self.duration_persistent = False

"""Implementation of the Gatekeeper card from Menagerie."""

from ..base_card import Card, CardCost, CardStats, CardType


class Gatekeeper(Card):
    """Gatekeeper - Action/Duration/Attack ($5)

    +$3
    At the start of your next turn, +$3.
    Until then, when another player gains an Action or Treasure card
    they don't have a copy of in Exile, they Exile it.
    """

    def __init__(self):
        super().__init__(
            name="Gatekeeper",
            cost=CardCost(coins=5),
            stats=CardStats(coins=3),
            types=[CardType.ACTION, CardType.DURATION, CardType.ATTACK],
        )
        self.duration_persistent = True

    def play_effect(self, game_state):
        player = game_state.current_player
        player.duration.append(self)

        # Attack: mark opponents as under gatekeeper attack
        for other in game_state.players:
            if other is not player:
                if not hasattr(other, "gatekeeper_attacks"):
                    other.gatekeeper_attacks = 0
                other.gatekeeper_attacks += 1

    def on_duration(self, game_state):
        player = game_state.current_player
        player.coins += 3

        # Remove attack effect from opponents
        for other in game_state.players:
            if other is not player:
                if hasattr(other, "gatekeeper_attacks"):
                    other.gatekeeper_attacks = max(0, other.gatekeeper_attacks - 1)

        self.duration_persistent = False

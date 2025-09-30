"""Implementation of the Highwayman duration attack."""

from ..base_card import Card, CardCost, CardStats, CardType


class Highwayman(Card):
    def __init__(self):
        super().__init__(
            name="Highwayman",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.DURATION, CardType.ATTACK],
        )
        self.duration_persistent = True
        self._affected_players: list = []

    def play_effect(self, game_state):
        player = game_state.current_player
        self._affected_players = []
        for other in game_state.players:
            if other is player:
                continue
            other.highwayman_attacks += 1
            self._affected_players.append(other)

        player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        for other in self._affected_players:
            other.highwayman_attacks = max(0, other.highwayman_attacks - 1)
        self._affected_players = []
        game_state.draw_cards(player, 3)
        self.duration_persistent = False

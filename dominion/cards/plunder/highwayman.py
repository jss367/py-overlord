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
        self.duration_persistent = False
        self._affected_players: list = []

    def play_effect(self, game_state):
        player = game_state.current_player

        def attack(target):
            target.highwayman_attacks += 1
            self._affected_players.append(target)

        for other in game_state.opponents_in_order(player):
            game_state.attack_player(other, attack, attacker=player, attack_card=self)
        player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        for other in self._affected_players:
            other.highwayman_attacks = max(0, other.highwayman_attacks - 1)
        self._affected_players = []
        if self in player.in_play:
            player.in_play.remove(self)
            game_state.discard_card(player, self)
        game_state.draw_cards(player, 3)

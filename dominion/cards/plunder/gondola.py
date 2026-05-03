"""Gondola from the Plunder expansion."""

from ..base_card import Card, CardCost, CardStats, CardType


class Gondola(Card):
    """$4 Treasure-Duration: Now or at start of next turn, +$2.
    When you gain this, you may play an Action card from your hand.
    """

    def __init__(self):
        super().__init__(
            name="Gondola",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.TREASURE, CardType.DURATION],
        )
        self.duration_persistent = True
        self._delayed = False

    def play_effect(self, game_state):
        player = game_state.current_player

        delay = False
        if hasattr(player.ai, "gondola_delay_coins"):
            delay = bool(player.ai.gondola_delay_coins(game_state, player))

        if delay:
            self._delayed = True
            player.duration.append(self)
        else:
            player.coins += 2

    def on_duration(self, game_state):
        player = game_state.current_player
        if self._delayed:
            player.coins += 2
            self._delayed = False
        self.duration_persistent = False

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)

        actions_in_hand = [c for c in player.hand if c.is_action]
        if not actions_in_hand:
            return

        choice = player.ai.choose_action(game_state, list(actions_in_hand) + [None])
        if choice is None or choice not in player.hand:
            return

        if player.actions <= 0:
            player.actions += 1

        player.hand.remove(choice)
        player.in_play.append(choice)
        choice.on_play(game_state)

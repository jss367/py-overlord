"""Implementation of the Mastermind duration."""

from ..base_card import Card, CardCost, CardStats, CardType


class Mastermind(Card):
    def __init__(self):
        super().__init__(
            name="Mastermind",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.DURATION],
        )
        self.duration_persistent = True

    def play_effect(self, game_state):
        game_state.current_player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        actions = [card for card in player.hand if card.is_action]
        if not actions:
            self.duration_persistent = False
            return

        choice = player.ai.choose_action(game_state, actions + [None])
        if choice is None:
            self.duration_persistent = False
            return

        if choice in player.hand:
            if not game_state.move_card_from_hand_to_play(player, choice):
                self.duration_persistent = False
                return
            for _ in range(3):
                game_state.play_action_indirectly(
                    player, choice, blocked_return_zone=player.hand
                )

        self.duration_persistent = False

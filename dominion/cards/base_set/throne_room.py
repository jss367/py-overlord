"""Implementation of the Throne Room multiplier."""

from ..base_card import Card, CardCost, CardStats, CardType


class ThroneRoom(Card):
    def __init__(self):
        super().__init__(
            name="Throne Room",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        actions_in_hand = [card for card in player.hand if card.is_action]

        if not actions_in_hand:
            return

        choice = player.ai.choose_action(game_state, actions_in_hand + [None])
        if choice is None or choice not in actions_in_hand:
            choice = actions_in_hand[0]

        if not game_state.move_card_from_hand_to_play(player, choice):
            return

        for _ in range(2):
            game_state.play_action_indirectly(
                player, choice, blocked_return_zone=player.hand
            )

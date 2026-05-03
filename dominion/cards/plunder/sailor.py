"""Sailor from the Plunder expansion."""

from ..base_card import Card, CardCost, CardStats, CardType


class Sailor(Card):
    """$4 Action-Duration: +1 Action. At start of next turn: +$2 and may trash a card from hand."""

    def __init__(self):
        super().__init__(
            name="Sailor",
            cost=CardCost(coins=4),
            stats=CardStats(actions=1),
            types=[CardType.ACTION, CardType.DURATION],
        )
        self.duration_persistent = True

    def play_effect(self, game_state):
        player = game_state.current_player
        player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        player.coins += 2

        if player.hand:
            choice = player.ai.choose_card_to_trash(
                game_state, list(player.hand) + [None]
            )
            if choice is not None and choice in player.hand:
                player.hand.remove(choice)
                game_state.trash_card(player, choice)

        self.duration_persistent = False

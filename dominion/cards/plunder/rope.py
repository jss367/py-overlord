"""Rope from the Plunder expansion."""

from ..base_card import Card, CardCost, CardStats, CardType


class Rope(Card):
    """$5 Treasure-Duration: +$1. Now and at start of next turn, +1 Card.
    Each turn, may trash a card from your hand.
    """

    def __init__(self):
        super().__init__(
            name="Rope",
            cost=CardCost(coins=5),
            stats=CardStats(coins=1),
            types=[CardType.TREASURE, CardType.DURATION],
        )
        self.duration_persistent = True

    def play_effect(self, game_state):
        player = game_state.current_player
        game_state.draw_cards(player, 1)
        self._maybe_trash(game_state, player)
        player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        game_state.draw_cards(player, 1)
        self._maybe_trash(game_state, player)
        self.duration_persistent = False

    @staticmethod
    def _maybe_trash(game_state, player):
        if not player.hand:
            return
        choice = player.ai.choose_card_to_trash(
            game_state, list(player.hand) + [None]
        )
        if choice is None or choice not in player.hand:
            return
        player.hand.remove(choice)
        game_state.trash_card(player, choice)

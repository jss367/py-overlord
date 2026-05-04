"""Goat — Pixie's Heirloom."""

from ...base_card import Card, CardCost, CardStats, CardType


class Goat(Card):
    """$1 Treasure-Heirloom: when you play this, you may trash a card from hand."""

    def __init__(self):
        super().__init__(
            name="Goat",
            cost=CardCost(coins=2),
            stats=CardStats(coins=1),
            types=[CardType.TREASURE, CardType.HEIRLOOM],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        if not player.hand:
            return
        choice = player.ai.choose_card_to_trash(game_state, list(player.hand))
        if choice is None or choice not in player.hand:
            return
        player.hand.remove(choice)
        game_state.trash_card(player, choice)

    def starting_supply(self, game_state) -> int:  # pragma: no cover
        return 0

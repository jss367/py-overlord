"""Implementation of the Moneylender card."""

from ..base_card import Card, CardCost, CardStats, CardType


class Moneylender(Card):
    """Action ($4): You may trash a Copper from your hand for +$3."""

    def __init__(self):
        super().__init__(
            name="Moneylender",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        copper = next((c for c in player.hand if c.name == "Copper"), None)
        if copper is None:
            return

        if not player.ai.should_trash_copper_for_moneylender(game_state, player):
            return

        player.hand.remove(copper)
        game_state.trash_card(player, copper)
        player.coins += 3
        game_state.log_callback(
            (
                "action",
                player.ai.name,
                "trashes a Copper for +$3 via Moneylender",
                {"coins": player.coins},
            )
        )

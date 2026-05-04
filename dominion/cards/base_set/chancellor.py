"""Implementation of the Chancellor (1E) card."""

from ..base_card import Card, CardCost, CardStats, CardType


class Chancellor(Card):
    """Action ($3): +$2. You may immediately put your deck into your discard pile."""

    def __init__(self):
        super().__init__(
            name="Chancellor",
            cost=CardCost(coins=3),
            stats=CardStats(coins=2),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        if not player.deck:
            return

        if not player.ai.should_chancellor_discard_deck(game_state, player):
            return

        cards_moved = list(player.deck)
        player.deck = []
        player.discard.extend(cards_moved)

        game_state.log_callback(
            (
                "action",
                player.ai.name,
                f"discards their deck via Chancellor ({len(cards_moved)} cards)",
                {"deck_size": len(cards_moved)},
            )
        )

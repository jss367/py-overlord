"""Implementation of Secret Chamber (1E)."""

from ..base_card import Card, CardCost, CardStats, CardType


class SecretChamber(Card):
    """Discard any number of cards. +$1 per card discarded.

    Reaction: When another player plays an Attack, you may reveal this
    from your hand. If you do, +2 Cards, then put 2 cards from your hand
    onto your deck.

    The Reaction logic lives in ``GameState._maybe_react_secret_chamber``.
    """

    def __init__(self):
        super().__init__(
            name="Secret Chamber",
            cost=CardCost(coins=2),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.REACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        if not player.hand:
            return

        # Choose any number of junk cards to discard for +$1 each.
        to_discard = player.ai.choose_secret_chamber_discards(
            game_state, player
        )
        # Filter to actual hand contents (defensive).
        actual: list[Card] = []
        for card in to_discard:
            if card in player.hand and card not in actual:
                actual.append(card)
        if not actual:
            return

        for card in actual:
            player.hand.remove(card)
            game_state.discard_card(player, card)
        player.coins += len(actual)

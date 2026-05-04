"""Scavenger — $4 Action that lets you reset your deck and topdeck a card from discard."""

from ..base_card import Card, CardCost, CardStats, CardType


class Scavenger(Card):
    """+$2. You may put your deck into your discard pile.

    Look through your discard pile. You may put a card from it on top of your
    deck.
    """

    def __init__(self):
        super().__init__(
            name="Scavenger",
            cost=CardCost(coins=4),
            stats=CardStats(coins=2),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        if player.deck and player.ai.should_scavenger_discard_deck(game_state, player):
            # Move whole deck to discard (no triggers; printed text is "put").
            player.discard.extend(player.deck)
            player.deck = []

        if not player.discard:
            return

        choice = player.ai.choose_card_to_topdeck_with_scavenger(
            game_state, player, list(player.discard)
        )
        if choice and choice in player.discard:
            player.discard.remove(choice)
            player.deck.append(choice)

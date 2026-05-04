"""Mystic — $5 Action that names a card and reveals deck top."""

from ..base_card import Card, CardCost, CardStats, CardType


class Mystic(Card):
    """+1 Action +$2. Name a card. Reveal the top card of your deck. If it
    matches, put it into your hand.
    """

    def __init__(self):
        super().__init__(
            name="Mystic",
            cost=CardCost(coins=5),
            stats=CardStats(actions=1, coins=2),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        named = player.ai.name_card_for_mystic(game_state, player)

        if not player.deck and player.discard:
            player.shuffle_discard_into_deck()
        if not player.deck:
            return

        top = player.deck[-1]
        if top.name == named:
            player.deck.pop()
            player.hand.append(top)

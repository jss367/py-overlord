"""Implementation of Courtyard."""

from ..base_card import Card, CardCost, CardStats, CardType


class Courtyard(Card):
    """+3 Cards. Put a card from your hand onto your deck."""

    def __init__(self):
        super().__init__(
            name="Courtyard",
            cost=CardCost(coins=2),
            stats=CardStats(cards=3),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        if not player.hand:
            return

        chosen = player.ai.choose_card_to_topdeck_for_courtyard(
            game_state, player, list(player.hand)
        )
        if chosen is None or chosen not in player.hand:
            return

        player.hand.remove(chosen)
        # Top of deck is the end of player.deck (deck.pop() draws).
        player.deck.append(chosen)

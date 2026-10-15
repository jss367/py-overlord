"""Night Watchman — $3 Night.

Look at top 5 cards. Discard or put back any in any order.
This is gained to your hand instead of your discard pile.
"""

from ..base_card import Card, CardCost, CardStats, CardType


class NightWatchman(Card):
    default_gain_destination = "hand"

    def __init__(self):
        super().__init__(
            name="Night Watchman",
            cost=CardCost(coins=3),
            stats=CardStats(),
            types=[CardType.NIGHT],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        revealed: list = []
        for _ in range(5):
            if not player.deck:
                player.shuffle_discard_into_deck()
            if not player.deck:
                break
            revealed.append(player.deck.pop())
        if not revealed:
            return
        discard, keep_ordered = player.ai.choose_cards_to_topdeck_or_discard(
            game_state, player, list(revealed)
        )
        # Validate
        keep = [c for c in revealed if c not in discard]
        if not keep_ordered or len(keep_ordered) != len(keep):
            keep_ordered = sorted(keep, key=lambda c: (c.cost.coins, c.name))
        for card in discard:
            game_state.discard_card(player, card)
        for card in keep_ordered:
            player.deck.append(card)

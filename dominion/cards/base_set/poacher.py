"""Implementation of the Poacher card."""

from ..base_card import Card, CardCost, CardStats, CardType


class Poacher(Card):
    """Action ($4): +1 Card, +1 Action, +$1.

    Discard a card per empty Supply pile.
    """

    def __init__(self):
        super().__init__(
            name="Poacher",
            cost=CardCost(coins=4),
            stats=CardStats(actions=1, cards=1, coins=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        empties = game_state.empty_piles
        if empties <= 0 or not player.hand:
            return

        to_discard = min(empties, len(player.hand))
        selected = player.ai.choose_cards_to_discard(
            game_state, player, list(player.hand), to_discard, reason="poacher"
        )

        discarded = 0
        for card in selected:
            if discarded >= to_discard:
                break
            if card in player.hand:
                player.hand.remove(card)
                game_state.discard_card(player, card)
                discarded += 1

        # Fallback: discard cheapest cards if AI didn't pick enough.
        while discarded < to_discard and player.hand:
            card = min(
                player.hand,
                key=lambda c: (c.is_action, c.is_treasure, c.cost.coins, c.name),
            )
            player.hand.remove(card)
            game_state.discard_card(player, card)
            discarded += 1

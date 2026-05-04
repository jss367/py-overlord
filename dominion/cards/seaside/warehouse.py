from ..base_card import Card, CardCost, CardStats, CardType


class Warehouse(Card):
    """Action ($3): +3 Cards, +1 Action. Discard 3 cards."""

    def __init__(self):
        super().__init__(
            name="Warehouse",
            cost=CardCost(coins=3),
            stats=CardStats(cards=3, actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        to_discard = min(3, len(player.hand))
        if to_discard <= 0:
            return

        selected = player.ai.choose_cards_to_discard(
            game_state, player, list(player.hand), to_discard, reason="warehouse"
        )

        discarded = 0
        for card in selected:
            if discarded >= to_discard:
                break
            if card in player.hand:
                player.hand.remove(card)
                game_state.discard_card(player, card)
                discarded += 1

        # Fallback: discard cheapest cards if AI didn't pick enough
        while discarded < to_discard and player.hand:
            card = min(player.hand, key=lambda c: (c.is_action, c.is_treasure, c.cost.coins, c.name))
            player.hand.remove(card)
            game_state.discard_card(player, card)
            discarded += 1

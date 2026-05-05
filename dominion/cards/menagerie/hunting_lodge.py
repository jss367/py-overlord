from ..base_card import Card, CardCost, CardStats, CardType


class HuntingLodge(Card):
    def __init__(self):
        super().__init__(
            name="Hunting Lodge",
            cost=CardCost(coins=5),
            stats=CardStats(cards=1, actions=2),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        """You may discard your hand for +5 Cards."""
        # Lazy import to avoid circular import (ways package imports cards
        # registry at top level).
        from dominion.ways.chameleon import chameleon_plus_cards

        player = game_state.current_player

        # AI decides whether to discard hand for 5 new cards
        # Generally good if hand is weak; always do it for simplicity
        # (the AI doesn't have a specific method for this, so we use a heuristic:
        #  discard if hand has 3 or fewer non-action cards worth playing)
        if not player.hand:
            # "+5 Cards" instruction — Way of the Chameleon swaps to +$5.
            chameleon_plus_cards(game_state, player, 5)
            return

        # Simple heuristic: discard unless hand already has Province-buying power
        total_coins = sum(c.stats.coins for c in player.hand if c.is_treasure)
        should_discard = total_coins < 8

        if should_discard:
            cards_to_discard = list(player.hand)
            player.hand = []
            game_state.discard_cards(player, cards_to_discard)
            # "+5 Cards" instruction — Way of the Chameleon swaps to +$5.
            chameleon_plus_cards(game_state, player, 5)

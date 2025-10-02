from ..base_card import Card, CardCost, CardStats, CardType


class HorseTraders(Card):
    """Generates +Buy and +Coins at the cost of discarding two cards."""

    def __init__(self):
        super().__init__(
            name="Horse Traders",
            cost=CardCost(coins=4),
            stats=CardStats(coins=3, buys=1),
            types=[CardType.ACTION, CardType.REACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        if not player.hand:
            return

        chosen = player.ai.choose_cards_to_discard(
            game_state, player, list(player.hand), 2, reason="horse_traders"
        )
        chosen = [card for card in chosen if card in player.hand][:2]

        # Ensure exactly two cards are discarded when possible
        if len(chosen) < 2:
            remaining = [card for card in player.hand if card not in chosen]
            remaining.sort(key=lambda c: (c.cost.coins, c.name))
            chosen.extend(remaining[: 2 - len(chosen)])

        for card in chosen:
            if card in player.hand:
                player.hand.remove(card)
                game_state.discard_card(player, card)

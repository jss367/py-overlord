from ..base_card import Card, CardCost, CardStats, CardType


class Plaza(Card):
    """Cantrip village that exchanges a Treasure for a Coin token."""

    def __init__(self):
        super().__init__(
            name="Plaza",
            cost=CardCost(coins=4),
            stats=CardStats(actions=1, cards=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        treasures = [card for card in player.hand if card.is_treasure]
        if not treasures:
            return

        selected = player.ai.choose_cards_to_discard(
            game_state, player, list(treasures), 1, reason="plaza"
        )
        discard_card = None
        for card in selected:
            if card in treasures:
                discard_card = card
                break
        if discard_card is None:
            discard_card = min(treasures, key=lambda c: (c.cost.coins, c.name))

        if discard_card not in player.hand:
            return

        player.hand.remove(discard_card)
        game_state.discard_card(player, discard_card)
        player.coin_tokens += 1

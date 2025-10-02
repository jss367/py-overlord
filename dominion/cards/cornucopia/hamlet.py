from ..base_card import Card, CardCost, CardStats, CardType


class Hamlet(Card):
    """Simplified implementation of the Hamlet card."""

    def __init__(self):
        super().__init__(
            name="Hamlet",
            cost=CardCost(coins=2),
            stats=CardStats(cards=1, actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        # Optionally discard a card for +1 Action
        if player.hand:
            discard = player.ai.choose_cards_to_discard(
                game_state, player, list(player.hand), 1, reason="hamlet_action"
            )
            if discard:
                card = discard[0]
                if card in player.hand:
                    player.hand.remove(card)
                    game_state.discard_card(player, card)
                    player.actions += 1

        # Optionally discard another card for +1 Buy
        if player.hand:
            discard = player.ai.choose_cards_to_discard(
                game_state, player, list(player.hand), 1, reason="hamlet_buy"
            )
            if discard:
                card = discard[0]
                if card in player.hand:
                    player.hand.remove(card)
                    game_state.discard_card(player, card)
                    player.buys += 1

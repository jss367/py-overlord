from ..base_card import Card, CardCost, CardStats, CardType


class Bishop(Card):
    """Simplified Bishop card."""

    def __init__(self):
        super().__init__(
            name="Bishop",
            cost=CardCost(coins=4),
            stats=CardStats(coins=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        if not player.hand:
            return

        card_to_trash = player.ai.choose_card_to_trash(game_state, player.hand)
        if card_to_trash is None:
            card_to_trash = player.hand[0]

        player.hand.remove(card_to_trash)
        game_state.trash_card(player, card_to_trash)
        player.vp_tokens += card_to_trash.cost.coins // 2

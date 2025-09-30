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

        # Bishop always awards one VP token on play
        player.vp_tokens += 1

        if player.hand:
            trash_choice = player.ai.choose_card_to_trash(
                game_state, list(player.hand) + [None]
            )
            if trash_choice:
                player.hand.remove(trash_choice)
                game_state.trash_card(player, trash_choice)
                player.vp_tokens += trash_choice.cost.coins // 2

        # Each other player may optionally trash a card from their hand
        for other in game_state.players:
            if other is player or not other.hand:
                continue
            choice = other.ai.choose_card_to_trash(game_state, list(other.hand) + [None])
            if choice and choice in other.hand:
                other.hand.remove(choice)
                game_state.trash_card(other, choice)

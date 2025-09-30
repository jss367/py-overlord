from ..base_card import Card, CardCost, CardStats, CardType


class TradeRoute(Card):
    def __init__(self):
        super().__init__(
            name="Trade Route",
            cost=CardCost(coins=3),
            stats=CardStats(buys=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        mat_tokens = getattr(game_state, "trade_route_mat_tokens", 0)
        player.coins += mat_tokens

        if not player.hand:
            return

        trash_choice = player.ai.choose_card_to_trash(game_state, list(player.hand) + [None])
        if trash_choice:
            player.hand.remove(trash_choice)
            game_state.trash_card(player, trash_choice)

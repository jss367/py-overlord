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

        from ..registry import get_card

        mat_tokens = 0
        for name, count in game_state.supply.items():
            card = get_card(name)
            if card.is_victory:
                if count < card.starting_supply(game_state):
                    mat_tokens += 1

        player.coins += mat_tokens

        if not player.hand:
            return

        trash_choice = player.ai.choose_card_to_trash(game_state, player.hand + [None])
        if trash_choice:
            player.hand.remove(trash_choice)
            game_state.trash_card(player, trash_choice)

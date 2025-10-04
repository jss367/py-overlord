from ..base_card import Card, CardCost, CardStats, CardType


class FarmersMarket(Card):
    def __init__(self):
        super().__init__(
            name="Farmers' Market",
            cost=CardCost(coins=3),
            stats=CardStats(buys=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        pile_tokens = game_state.farmers_market_pile_tokens
        options = ["coins", "vp"]
        choice = player.ai.choose_farmers_market_option(
            game_state, player, options, pile_tokens
        )
        if choice not in options:
            choice = "coins"

        if choice == "vp":
            if pile_tokens > 0:
                player.vp_tokens += pile_tokens
                if self in player.in_play:
                    player.in_play.remove(self)
                game_state.trash_card(player, self)
            game_state.farmers_market_pile_tokens = 0
        else:
            player.coins += pile_tokens

        game_state.farmers_market_pile_tokens += 1

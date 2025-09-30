from ..base_card import Card, CardCost, CardStats, CardType


class IllGottenGains(Card):
    def __init__(self):
        super().__init__(
            name="Ill-Gotten Gains",
            cost=CardCost(coins=5),
            stats=CardStats(coins=1, buys=1),
            types=[CardType.TREASURE],
        )

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)

        from ..registry import get_card

        if game_state.supply.get("Copper", 0) > 0:
            game_state.supply["Copper"] -= 1
            game_state.gain_card(player, get_card("Copper"))

        for other in game_state.players:
            if other is player:
                continue
            game_state.give_curse_to_player(other)

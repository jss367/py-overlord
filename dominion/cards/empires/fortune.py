from ..base_card import Card, CardCost, CardStats, CardType


class Fortune(Card):
    def __init__(self):
        super().__init__(
            name="Fortune",
            cost=CardCost(debt=8),
            stats=CardStats(buys=1),
            types=[CardType.TREASURE],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        if not getattr(player, "fortune_doubled_this_turn", False):
            player.coins *= 2
            player.fortune_doubled_this_turn = True

    def on_gain(self, game_state, player):
        from ..registry import get_card

        super().on_gain(game_state, player)

        if game_state.supply.get("Gold", 0) <= 0:
            return

        for card in list(player.in_play):
            if card.name != "Gladiator":
                continue
            if game_state.supply.get("Gold", 0) <= 0:
                break
            game_state.supply["Gold"] -= 1
            game_state.gain_card(player, get_card("Gold"))

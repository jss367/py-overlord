from ..base_card import Card, CardCost, CardStats, CardType


class Skulk(Card):
    """Implementation of the Nocturne attack ``Skulk``."""

    def __init__(self):
        super().__init__(
            name="Skulk",
            cost=CardCost(coins=4),
            stats=CardStats(buys=1),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        targets = [other for other in game_state.players if other is not player]
        if not targets:
            return

        hex_name = game_state.draw_hex()
        if not hex_name:
            return

        def attack(target):
            game_state.resolve_hex(target, hex_name)

        for other in targets:
            game_state.attack_player(other, attack)

        game_state.discard_hex(hex_name)

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)
        if game_state.supply.get("Gold", 0) > 0:
            from ..registry import get_card

            game_state.supply["Gold"] -= 1
            gold = get_card("Gold")
            game_state.gain_card(player, gold)

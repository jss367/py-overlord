from ..base_card import Card, CardCost, CardStats, CardType


class Soothsayer(Card):
    """Gold gainer and curser that lets opponents draw."""

    def __init__(self):
        super().__init__(
            name="Soothsayer",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player

        if game_state.supply.get("Gold", 0) > 0:
            game_state.supply["Gold"] -= 1
            game_state.gain_card(player, get_card("Gold"))

        for other in game_state.players:
            if other is player:
                continue

            def attack(target):
                gained = game_state.give_curse_to_player(target, to_hand=True)
                if gained:
                    game_state.draw_cards(target, 1)

            game_state.attack_player(other, attack)

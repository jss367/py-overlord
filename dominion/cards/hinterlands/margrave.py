from ..base_card import Card, CardCost, CardStats, CardType


class Margrave(Card):
    def __init__(self):
        super().__init__(
            name="Margrave",
            cost=CardCost(coins=5),
            stats=CardStats(cards=3, buys=1),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        def attack(target):
            game_state.draw_cards(target, 1)
            from ._discard import discard_from_hand

            discard_from_hand(game_state, target, max(0, len(target.hand) - 3), "margrave")

        for other in game_state.players:
            if other is player:
                continue
            game_state.attack_player(other, attack)

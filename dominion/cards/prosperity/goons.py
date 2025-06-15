from ..base_card import Card, CardCost, CardStats, CardType


class Goons(Card):
    def __init__(self):
        super().__init__(
            name="Goons",
            cost=CardCost(coins=6),
            stats=CardStats(coins=2, buys=1),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        player.goons_played += 1

        def attack_target(target):
            while len(target.hand) > 3:
                card = target.hand.pop()
                target.discard.append(card)

        for other in game_state.players:
            if other is player:
                continue
            game_state.attack_player(other, attack_target)

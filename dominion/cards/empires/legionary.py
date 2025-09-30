from ..base_card import Card, CardCost, CardStats, CardType


class Legionary(Card):
    def __init__(self):
        super().__init__(
            name="Legionary",
            cost=CardCost(coins=5),
            stats=CardStats(coins=3),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        def attack(target):
            if any(card.name == "Gold" for card in target.hand):
                return
            while len(target.hand) > 2:
                game_state.discard_card(target, target.hand.pop())

        for other in game_state.players:
            if other is player:
                continue
            game_state.attack_player(other, attack)

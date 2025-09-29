from ..base_card import Card, CardCost, CardStats, CardType


class Forum(Card):
    def __init__(self):
        super().__init__(
            name="Forum",
            cost=CardCost(coins=5),
            stats=CardStats(actions=1, cards=3),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        for _ in range(2):
            if player.hand:
                player.discard.append(player.hand.pop())

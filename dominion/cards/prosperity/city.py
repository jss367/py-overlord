from ..base_card import Card, CardCost, CardStats, CardType


class City(Card):
    def __init__(self):
        super().__init__(
            name="City",
            cost=CardCost(coins=5),
            stats=CardStats(actions=2, cards=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        empty_piles = sum(1 for count in game_state.supply.values() if count == 0)

        if empty_piles >= 1:
            game_state.draw_cards(player, 1)
            player.coins += 1

        if empty_piles >= 2:
            player.buys += 1
            player.coins += 1

from ..base_card import Card, CardCost, CardStats, CardType


class Colony(Card):
    def __init__(self):
        super().__init__(
            name="Colony",
            cost=CardCost(coins=11),
            stats=CardStats(vp=10),
            types=[CardType.VICTORY],
        )

    def starting_supply(self, game_state) -> int:
        n_players = len(game_state.players)
        if n_players <= 2:
            return 8
        if n_players <= 4:
            return 12
        return 12 + 3 * (n_players - 4)

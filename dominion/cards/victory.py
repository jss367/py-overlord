from .base_card import Card, CardCost, CardStats, CardType


class Estate(Card):
    def __init__(self):
        super().__init__(name="Estate", cost=CardCost(coins=2), stats=CardStats(vp=1), types=[CardType.VICTORY])

    def starting_supply(self, game_state) -> int:
        return 8 if len(game_state.players) <= 2 else 12


class Duchy(Card):
    def __init__(self):
        super().__init__(name="Duchy", cost=CardCost(coins=5), stats=CardStats(vp=3), types=[CardType.VICTORY])

    def starting_supply(self, game_state) -> int:
        return 8 if len(game_state.players) <= 2 else 12


class Province(Card):
    def __init__(self):
        super().__init__(name="Province", cost=CardCost(coins=8), stats=CardStats(vp=6), types=[CardType.VICTORY])

    def starting_supply(self, game_state) -> int:
        n_players = len(game_state.players)
        if n_players <= 2:
            return 8
        elif n_players <= 4:
            return 12
        return 15


class Curse(Card):
    def __init__(self):
        super().__init__(name="Curse", cost=CardCost(coins=0), stats=CardStats(vp=-1), types=[CardType.CURSE])

    def starting_supply(self, game_state) -> int:
        return 10 * (len(game_state.players) - 1)

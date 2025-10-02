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

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)

        duchess_supply = game_state.supply.get("Duchess", 0)
        if duchess_supply <= 0:
            return

        from .registry import get_card

        game_state.supply["Duchess"] = duchess_supply - 1
        game_state.gain_card(player, get_card("Duchess"))


class Province(Card):
    def __init__(self):
        super().__init__(name="Province", cost=CardCost(coins=8), stats=CardStats(vp=6), types=[CardType.VICTORY])

    def starting_supply(self, game_state) -> int:
        n_players = len(game_state.players)
        if n_players <= 2:
            return 8
        if n_players <= 4:
            return 12
        # Official rules add three Provinces for each player beyond four
        return 12 + 3 * (n_players - 4)


class Curse(Card):
    def __init__(self):
        super().__init__(name="Curse", cost=CardCost(coins=0), stats=CardStats(vp=-1), types=[CardType.CURSE])

    def starting_supply(self, game_state) -> int:
        n_players = len(game_state.players)
        if n_players <= 1:
            return 10
        return 10 * (n_players - 1)

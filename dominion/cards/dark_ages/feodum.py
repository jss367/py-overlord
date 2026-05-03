from ..base_card import Card, CardCost, CardStats, CardType


class Feodum(Card):
    """Victory card worth 1 VP per 3 Silvers you have (rounded down).

    When trashed, gain 3 Silvers.
    """

    def __init__(self):
        super().__init__(
            name="Feodum",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.VICTORY],
        )

    def starting_supply(self, game_state) -> int:
        return 8 if len(game_state.players) <= 2 else 12

    def get_victory_points(self, player) -> int:
        silvers = sum(1 for card in player.all_cards() if card.name == "Silver")
        return silvers // 3

    def on_trash(self, game_state, player):
        from ..registry import get_card

        for _ in range(3):
            if game_state.supply.get("Silver", 0) <= 0:
                break
            game_state.supply["Silver"] -= 1
            game_state.gain_card(player, get_card("Silver"))

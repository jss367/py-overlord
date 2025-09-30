from ..base_card import Card, CardCost, CardStats, CardType


class Spoils(Card):
    """Non-supply treasure returned after play."""

    def __init__(self):
        super().__init__(
            name="Spoils",
            cost=CardCost(coins=0),
            stats=CardStats(coins=3),
            types=[CardType.TREASURE],
        )

    def may_be_bought(self, game_state) -> bool:  # pragma: no cover - not in supply
        return False

    def starting_supply(self, game_state) -> int:
        return 15

    def play_effect(self, game_state):
        player = game_state.current_player
        if self in player.in_play:
            player.in_play.remove(self)
        game_state.supply["Spoils"] = game_state.supply.get("Spoils", 0) + 1

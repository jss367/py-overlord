"""Lucky Coin — Fool's Heirloom."""

from ...base_card import Card, CardCost, CardStats, CardType


class LuckyCoin(Card):
    """$1 Treasure-Heirloom: when you play this, gain a Silver."""

    def __init__(self):
        super().__init__(
            name="Lucky Coin",
            cost=CardCost(coins=4),
            stats=CardStats(coins=1),
            types=[CardType.TREASURE, CardType.HEIRLOOM],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        if game_state.supply.get("Silver", 0) <= 0:
            return
        from ...registry import get_card

        game_state.supply["Silver"] -= 1
        game_state.gain_card(player, get_card("Silver"))

    def starting_supply(self, game_state) -> int:  # pragma: no cover
        return 0

"""Bandit Camp — $5 village that gains a Spoils."""

from ..base_card import Card, CardCost, CardStats, CardType


class BanditCamp(Card):
    """+1 Card +2 Actions. Gain a Spoils."""

    def __init__(self):
        super().__init__(
            name="Bandit Camp",
            cost=CardCost(coins=5),
            stats=CardStats(cards=1, actions=2),
            types=[CardType.ACTION],
        )

    def get_additional_piles(self) -> dict[str, int]:
        return {"Spoils": 15}

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        if game_state.supply.get("Spoils", 0) > 0:
            game_state.supply["Spoils"] -= 1
            game_state.gain_card(player, get_card("Spoils"))

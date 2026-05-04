"""Wayfarer - Action from Menagerie."""

from ..base_card import Card, CardCost, CardStats, CardType


class Wayfarer(Card):
    """+3 Cards. You may gain a Silver. This is the same cost as the most
    recently gained card on your turn.
    """

    def __init__(self):
        super().__init__(
            name="Wayfarer",
            cost=CardCost(coins=6),
            stats=CardStats(cards=3),
            types=[CardType.ACTION],
        )

    def cost_modifier(self, game_state, player) -> int:
        last_name = None
        if getattr(player, "gained_cards_this_turn", None):
            last_name = player.gained_cards_this_turn[-1]
        if not last_name:
            return 0
        from ..registry import get_card

        try:
            other = get_card(last_name)
        except ValueError:
            return 0
        # Cost matches the most recent gain. delta = other.cost - 6.
        return other.cost.coins - self.cost.coins

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        if game_state.supply.get("Silver", 0) <= 0:
            return
        if not player.ai.should_gain_silver_for_wayfarer(game_state, player):
            return
        game_state.supply["Silver"] -= 1
        game_state.gain_card(player, get_card("Silver"))

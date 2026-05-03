"""Shaman from the Plunder expansion."""

from ..base_card import Card, CardCost, CardStats, CardType


class Shaman(Card):
    """$2 Action: +1 Action, +$1. Gain a card from the trash costing up to $6."""

    def __init__(self):
        super().__init__(
            name="Shaman",
            cost=CardCost(coins=2),
            stats=CardStats(actions=1, coins=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        candidates = [c for c in game_state.trash if c.cost.coins <= 6]
        if not candidates:
            return

        choice = player.ai.choose_action(game_state, list(candidates) + [None])
        if choice is None or choice not in game_state.trash:
            return

        game_state.trash.remove(choice)
        game_state.gain_card(player, choice, from_supply=False)

"""Duplicate (Adventures) — $4 Action-Reserve."""

from ..base_card import Card, CardCost, CardStats, CardType


class Duplicate(Card):
    def __init__(self):
        super().__init__(
            name="Duplicate",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.RESERVE],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        game_state.set_aside_on_tavern(player, self)

    def on_call_from_tavern(self, game_state, player, trigger, *args, **kwargs):
        if trigger != "gain":
            return False
        if not args:
            return False
        gained_card = args[0]
        if gained_card is None or gained_card.cost.coins > 6:
            return False
        if game_state.supply.get(gained_card.name, 0) <= 0:
            return False
        if not player.ai.should_call_from_tavern(
            game_state, player, self, trigger, *args
        ):
            return False
        # Move from tavern mat to discard FIRST, before gaining, to prevent
        # the resulting gain trigger from re-entering this card.
        from ..registry import get_card

        game_state.call_from_tavern(player, self)
        game_state.supply[gained_card.name] -= 1
        game_state.gain_card(player, get_card(gained_card.name))
        return True

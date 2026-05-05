"""Druid — $2 Action.

+1 Buy. Receive one of the 3 Boons set aside at game start.
"""

from ..base_card import Card, CardCost, CardStats, CardType


class Druid(Card):
    uses_boons = True

    def __init__(self):
        super().__init__(
            name="Druid",
            cost=CardCost(coins=2),
            stats=CardStats(buys=1),
            types=[CardType.ACTION, CardType.FATE],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        boons = list(getattr(game_state, "druid_boons", []))
        if not boons:
            return
        choice = player.ai.choose_druid_boon(game_state, player, boons)
        if not choice or choice not in boons:
            choice = boons[0]
        # Apply the Boon. Druid's set-aside Boons are NEVER shuffled into the
        # Boons discard pile — they remain set aside for the entire game so
        # future Druid plays keep choosing among the same three Boons.
        # Persistent Boons (Field's/Forest's/River's Gift) still need to fire
        # their next-turn effect for the receiving player, but we attach them
        # to ``player.druid_active_boons`` (rather than ``active_boons``) so
        # the start-of-turn cleanup applies the bonus without discarding the
        # Boon name.
        from dominion.boons import resolve_boon, is_persistent_boon

        game_state.log_callback(
            ("action", player.ai.name, f"Druid receives Boon: {choice}", {})
        )
        resolve_boon(choice, game_state, player)
        if is_persistent_boon(choice):
            if not hasattr(player, "druid_active_boons"):
                player.druid_active_boons = []
            player.druid_active_boons.append(choice)

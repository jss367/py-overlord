"""Distant Lands (Adventures) — $5 Action-Reserve-Victory."""

from ..base_card import Card, CardCost, CardStats, CardType


class DistantLands(Card):
    def __init__(self):
        super().__init__(
            name="Distant Lands",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.RESERVE, CardType.VICTORY],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        game_state.set_aside_on_tavern(player, self)
        player.distant_lands_played += 1

    def get_victory_points(self, player) -> int:
        # Worth 4 VP if on the Tavern mat at game end, otherwise 0.
        if self in getattr(player, "tavern_mat", []):
            return 4
        return 0

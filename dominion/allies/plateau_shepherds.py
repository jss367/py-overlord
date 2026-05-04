from .base_ally import Ally


class PlateauShepherds(Ally):
    """4 VP per pair (Favor + card costing $2).

    Implementation: Plateau Shepherds gives end-game scoring; we add a
    ``score_bonus`` hook called by ``GameState.compute_final_scores``.
    No turn-time effect.
    """

    def __init__(self):
        super().__init__("Plateau Shepherds")

    def score_bonus(self, game_state, player) -> int:
        favors = player.favors
        twos = sum(
            1 for c in player.all_cards()
            if c.cost.coins == 2 and c.cost.potions == 0 and c.cost.debt == 0
        )
        pairs = min(favors, twos)
        return 4 * pairs

"""Fleet: after the game ends, there's an extra round of turns, but only
Fleet players take part."""

from dominion.cards.base_card import CardCost

from .base_project import Project


class Fleet(Project):
    def __init__(self) -> None:
        super().__init__("Fleet", CardCost(coins=5))

    # The bookkeeping for the Fleet extra round lives in
    # ``GameState.is_game_over`` and ``handle_cleanup_phase``.

from dominion.cards.base_card import CardCost
from .base_project import Project


class Sewers(Project):
    """When you trash a card other than with this, you may trash a card from your hand.

    The "other than with this" clause means the extra trash never re-triggers
    Sewers, so one trash yields at most one extra trash (other trash triggers
    such as Tomb, Priest, and Market Square still see both).
    """

    def __init__(self):
        super().__init__("Sewers", CardCost(coins=3))
        self._resolving = False

    def on_trash(self, game_state, player, card) -> None:
        if self._resolving or not player.hand:
            return
        choice = player.ai.choose_card_to_trash(game_state, player.hand + [None])
        if not choice:
            return
        self._resolving = True
        try:
            player.hand.remove(choice)
            game_state.trash_card(player, choice)
        finally:
            self._resolving = False

from dominion.cards.base_card import CardCost
from .base_project import Project


class Sewers(Project):
    """When you trash a card other than with this, you may trash a card from your hand.

    Only the card Sewers itself trashes is exempt from re-triggering Sewers.
    Other trashes that happen while that card resolves (Tomb, Priest, and
    Market Square see it; a Pious-pile trash is a separate trash) still get
    their own Sewers trigger.
    """

    def __init__(self):
        super().__init__("Sewers", CardCost(coins=3))
        self._own_trash = None

    def on_trash(self, game_state, player, card) -> None:
        if card is self._own_trash or not player.hand:
            return
        choice = player.ai.choose_card_to_trash(game_state, player.hand + [None])
        if not choice:
            return
        player.hand.remove(choice)
        previous, self._own_trash = self._own_trash, choice
        try:
            game_state.trash_card(player, choice)
        finally:
            self._own_trash = previous

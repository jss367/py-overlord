"""Common base for Allies-style split piles (Augurs, Clashes, Forts,
Odysseys, Townsfolk, Wizards).

Each pile has 4 named cards stacked from top to bottom. The top card
is the only one that may be bought; once that pile name is empty, the
next one becomes buyable. ``GameState.setup_supply`` detects these
piles and adds the partner names automatically.
"""

from typing import ClassVar

from ..base_card import Card


class AlliesSplitCard(Card):
    """Base class for the four-card Allies split piles.

    Subclasses must set ``pile_order`` to the tuple of names from top to
    bottom and ``upper_partners`` to the names of the cards above this
    one in the pile.
    """

    pile_order: ClassVar[tuple[str, ...]] = ()
    upper_partners: ClassVar[tuple[str, ...]] = ()

    def starting_supply(self, game_state) -> int:
        # Each Allies split pile is 4 cards per name regardless of player
        # count (matches how Wizards is sized).
        return 4 if len(game_state.players) <= 2 else 5

    def may_be_bought(self, game_state) -> bool:
        for partner in self.upper_partners:
            if game_state.supply.get(partner, 0) > 0:
                return False
        return super().may_be_bought(game_state)


def grant_favor(player) -> None:
    player.favors += 1

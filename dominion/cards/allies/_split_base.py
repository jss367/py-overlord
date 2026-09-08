"""Base for the six rotating Allies piles."""

from typing import ClassVar

from ..base_card import Card, CardType


class AlliesSplitCard(Card):
    pile_order: ClassVar[tuple[str, ...]] = ()
    upper_partners: ClassVar[tuple[str, ...]] = ()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        families = {
            "Herb Gatherer": CardType.AUGUR,
            "Battle Plan": CardType.CLASH,
            "Tent": CardType.FORT,
            "Old Map": CardType.ODYSSEY,
            "Town Crier": CardType.TOWNSFOLK,
            "Student": CardType.WIZARD,
        }
        self.types.append(families[self.pile_order[0]])

    def starting_supply(self, game_state):
        return 4

    def may_be_bought(self, game_state):
        return game_state.top_supply_card(self.name) in (
            None,
            self.name,
        ) and super().may_be_bought(game_state)

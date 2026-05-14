"""Inspiring Festival Engine strategy.

Designed for boards that pair the Plunder Inspiring trait on Supplies
with Festival / Council Room / Smithy and a Vault payload (see
``boards/inspiring_supplies.txt``). Supplies (a $1 Treasure) gains a
Horse on-buy and, with Inspiring on its pile, lets you play an Action
from hand after each Supplies play — so the cantrip-into-Action pattern
fuels a Festival/Council Room engine well.

Empirically the strongest of the candidates tried on this 10-card Colony
board with Shelters: beats the closest Big Money + Smithy + Vault build
~54%-46% head-to-head over 300 games.
"""

from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


def _colonies_left(op: str, amount: int):
    cmp = PriorityRule._OP_MAP[op]
    return lambda state, _player: cmp(state.supply.get("Colony", 0), amount)


class InspiringFestivalEngine(EnhancedStrategy):
    """Festival / Council Room draw engine into Colonies."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "Inspiring Festival Engine"
        self.description = (
            "Festival + Council Room + Smithy draw engine with Vault payload; "
            "uses Inspiring-Supplies for Horse generation and free Action plays."
        )
        self.version = "1.1"

        self.gain_priority = [
            PriorityRule("Colony"),
            PriorityRule("Province", _colonies_left("<=", 3)),
            PriorityRule("Platinum"),
            PriorityRule("Gold"),
            PriorityRule("Council Room", PriorityRule.max_in_deck("Council Room", 2)),
            PriorityRule("Festival", PriorityRule.max_in_deck("Festival", 3)),
            PriorityRule("Vault", PriorityRule.max_in_deck("Vault", 2)),
            PriorityRule("Smithy", PriorityRule.max_in_deck("Smithy", 2)),
            PriorityRule("Hunter", PriorityRule.max_in_deck("Hunter", 1)),
            PriorityRule("Mystic", PriorityRule.max_in_deck("Mystic", 1)),
            PriorityRule("Duchy", _colonies_left("<=", 2)),
            PriorityRule("Supplies", PriorityRule.max_in_deck("Supplies", 3)),
            PriorityRule("Silver"),
        ]
        self.action_priority = [
            PriorityRule("Festival"),
            PriorityRule("Horse"),
            PriorityRule("Necropolis"),
            PriorityRule("Hunter"),
            PriorityRule("Mystic"),
            PriorityRule("Vault"),
            PriorityRule("Council Room"),
            PriorityRule("Smithy"),
            PriorityRule("Storeroom"),
            PriorityRule("Infirmary"),
            PriorityRule("Change"),
        ]
        self.treasure_priority = [
            PriorityRule("Platinum"),
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Supplies"),
            PriorityRule("Copper"),
        ]


def create_inspiring_festival_engine() -> EnhancedStrategy:
    return InspiringFestivalEngine()

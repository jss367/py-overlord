"""Focused Cobbler policies with separate purchase and free-gain targets."""

from dominion.strategy.enhanced_strategy import EnhancedStrategy
from dominion.strategy.strategies.shepherd_tragic_hero import ShepherdTragicHero


def create_cobbler_shepherd_growth() -> EnhancedStrategy:
    """Focused-search winner selected before independent validation."""
    strategy = ShepherdTragicHero(
        shepherd=1,
        hero=2,
        monastery=0,
        silver=99,
        estate=3,
        cobbler=2,
        cobbler_shepherds=4,
        cobbler_estates=5,
        cobbler_adaptive=True,
        priority="night",
        opening="Tragic Hero",
        monastery_timing="spare",
    )
    strategy.name = "Cobbler Shepherd Growth"
    strategy.description = (
        "Two Cobblers gain Shepherds when the hand needs draw, up to four owned; "
        "otherwise gain Estates up to five, then Silver. Maintain two Tragic Heroes. "
        "Switch to scoring at three Provinces remaining. "
        "See the Cobbler and Shepherd comparison guide for held-out results."
    )
    active = {
        "Cobbler",
        "Shepherd",
        "Tragic Hero",
        "Wish",
        "Magic Lamp",
        "Pasture",
        "Gold",
        "Silver",
        "Copper",
        "Province",
        "Duchy",
        "Estate",
    }
    for attr in ("action_priority", "treasure_priority", "gain_priority"):
        setattr(
            strategy, attr, [r for r in getattr(strategy, attr) if r.card in active]
        )
    return strategy

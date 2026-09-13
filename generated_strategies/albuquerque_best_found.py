"""Best strategy found for the Albuquerque board (``boards/albuquerque.txt``).

See ``reports/strategies/albuquerque-strategy-guide.html`` for the search
and validation.

Chassis: the Masquerade Bridge Engine seed with the two hand-search
adjustments that measured best (two King's Courts instead of three, four
Bridges instead of six). Open Masquerade; buy Wharves, Wandering Minstrels
to cover the terminals, Bridges and King's Court; green once a King's Court
and three payload cards are in the deck (or from turn 12). King's Court
prefers another King's Court when four Actions are in hand, then Bridge,
then Wharf. Masquerade passes Curses, Ruins, Estates and Coppers; Coppers
are trashed only while the deck keeps more than $6 of Treasure (more than
$3 once three Bridges are owned). With two piles empty and the lead, drain
the smallest pile to end the game.
"""

from dominion.strategy.enhanced_strategy import EnhancedStrategy
from dominion.strategy.strategies.albuquerque_seeds import _BridgeEngine


class AlbuquerqueBestFound(_BridgeEngine):
    opener = "Masquerade"
    gain_kwargs = {"kc": 2, "bridge": 4}
    multiplier_first = "Bridge"

    def __init__(self) -> None:
        super().__init__()
        self.name = "Albuquerque Best Found"
        self.description = (
            "Masquerade opener into a Wandering Minstrel / Wharf / Bridge engine "
            "with two King's Courts; greens once a King's Court and three payload "
            "cards are owned."
        )
        self.version = "1.0"


def create_albuquerque_best_found() -> EnhancedStrategy:
    return AlbuquerqueBestFound()

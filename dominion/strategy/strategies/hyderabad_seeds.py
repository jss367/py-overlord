"""Island seeds for the Hyderabad board (``boards/hyderabad.txt``).

Kingdom: Ducat, Scrap, Stockpile, Patron, Priest, River Shrine,
Village Green, Rice Broker, Scepter, Scholar — with the Silos project,
Way of the Otter, and the Progress prophecy pinned (River Shrine is the
Omen that deals it).

Board texture
-------------
- Way of the Otter turns every Action into "+2 Cards", so even weak
  Actions are never dead — draw is cheap on this board.
- Progress (once the 5 Sun tokens are gone) topdecks every gain. That
  supercharges money (buy Gold, draw it next turn) but also means green
  buys clog the next hand — Scholar's discard-and-draw-7 shrugs that off.
- Scholar + Village Green combo: Scholar discards your hand, and each
  discarded Village Green may be revealed and played (+1 Card +2
  Actions), so Scholar can chain instead of ending the turn.
- Priest turns extra trashes into +$2 each; Rice Broker and Scrap
  provide the extra trashes and Scepter can replay Priest.
- Stockpile/Ducat give cheap +Buy money; the Stockpile pile self-drains
  (each play exiles it), so it is natural three-pile pressure.

Each seed below is a distinct theory of the kingdom for the island
model. The GA is expected to build on or prune each one.
"""

from dominion.strategy.enhanced_strategy import (
    EnhancedStrategy,
    PriorityRule,
    WayRule,
)


class HyderabadScholarMoney(EnhancedStrategy):
    """Big Money chassis with Scholar as the draw engine.

    Progress makes this better than it looks: every Gold bought lands on
    top of the deck, and Scholar refuses to keep a clogged hand.
    """

    def __init__(self) -> None:
        super().__init__()
        self.name = "Hyderabad Scholar Money"
        self.description = "Money + Scholar mass-draw riding Progress topdecks."
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule("Province", PriorityRule.resources("coins", ">=", 8)),
            PriorityRule("Gold"),
            PriorityRule("Scholar", PriorityRule.max_in_deck("Scholar", 2)),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 4)),
            PriorityRule("Silver"),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
        ]

        self.action_priority = [
            # Only cash in Scholar when the hand is weak; a hand full of
            # treasure should just be spent.
            PriorityRule("Scholar", PriorityRule.treasures_in_hand("<=", 3)),
        ]

        self.treasure_priority = [
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Copper"),
        ]


class HyderabadGreenScholarEngine(EnhancedStrategy):
    """Village Green + Scholar draw engine with Patron payload.

    Scholar's discard triggers Village Green's reaction, so each Scholar
    is "+7 Cards and re-play the villages you discarded". Patron supplies
    +$2 and Villagers to keep terminals flowing.
    """

    def __init__(self) -> None:
        super().__init__()
        self.name = "Hyderabad Green Scholar Engine"
        self.description = (
            "Village Green/Scholar draw engine; Patron coins and Villagers."
        )
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule("Province", PriorityRule.resources("coins", ">=", 8)),
            PriorityRule("Scholar", PriorityRule.max_in_deck("Scholar", 3)),
            PriorityRule("Village Green", PriorityRule.max_in_deck("Village Green", 5)),
            PriorityRule("Patron", PriorityRule.max_in_deck("Patron", 3)),
            PriorityRule("Gold"),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 3)),
            PriorityRule("Silver", PriorityRule.turn_number("<=", 6)),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
        ]

        self.action_priority = [
            PriorityRule("Village Green"),
            PriorityRule("Patron", PriorityRule.excess_actions(">=", 1)),
            PriorityRule("Scholar"),
            PriorityRule("Patron"),
        ]

        self.treasure_priority = [
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Copper"),
        ]


class HyderabadPriestPayload(EnhancedStrategy):
    """Trash-for-profit money: Priest first, then every further trash pays $2.

    Rice Broker supplies a second trash that also draws; Scepter can
    echo Priest. Thin fast, then buy green off big Priest turns.
    """

    def __init__(self) -> None:
        super().__init__()
        self.name = "Hyderabad Priest Payload"
        self.description = "Priest/Rice Broker trash-for-profit money."
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule("Province", PriorityRule.resources("coins", ">=", 8)),
            PriorityRule("Gold"),
            PriorityRule("Priest", PriorityRule.max_in_deck("Priest", 2)),
            PriorityRule("Rice Broker", PriorityRule.max_in_deck("Rice Broker", 1)),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 4)),
            PriorityRule("Silver"),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
        ]

        self.action_priority = [
            # Priest before the other trashers so their trashes pay +$2.
            PriorityRule("Priest"),
            PriorityRule("Rice Broker"),
        ]

        self.treasure_priority = [
            PriorityRule("Scepter"),
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Copper"),
        ]

        self.trash_priority = [
            PriorityRule("Estate", PriorityRule.provinces_left(">", 2)),
            PriorityRule("Copper"),
        ]


class HyderabadStockpileRush(EnhancedStrategy):
    """Stockpile/Ducat buy-heavy money rush.

    Stockpile is $3 +Buy that exiles itself, so the pile drains toward a
    three-pile ending while Progress topdecks every green buy for the
    opponent to choke on. Get in, green early, end it.
    """

    def __init__(self) -> None:
        super().__init__()
        self.name = "Hyderabad Stockpile Rush"
        self.description = "Stockpile/Ducat rush with early green and pile pressure."
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule("Province", PriorityRule.resources("coins", ">=", 8)),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 6)),
            PriorityRule("Stockpile"),
            PriorityRule("Ducat"),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 4)),
        ]

        self.treasure_priority = [
            PriorityRule("Stockpile"),
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Ducat"),
            PriorityRule("Copper"),
        ]


class HyderabadOtterBrokerEngine(EnhancedStrategy):
    """Thin Rice Broker deck that leans on Way of the Otter for draw.

    Rice Broker trashes Coppers for +2 Cards while junk remains; once
    the deck is clean, Rice Broker and Patron are played as Otters
    (+2 Cards) instead of their weak printed effects.
    """

    def __init__(self) -> None:
        super().__init__()
        self.name = "Hyderabad Otter Broker Engine"
        self.description = (
            "Rice Broker thinning into Otter-lab draw with Patron payload."
        )
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule("Province", PriorityRule.resources("coins", ">=", 8)),
            PriorityRule("Rice Broker", PriorityRule.max_in_deck("Rice Broker", 3)),
            PriorityRule("Patron", PriorityRule.max_in_deck("Patron", 3)),
            PriorityRule("Gold"),
            PriorityRule("Village Green", PriorityRule.max_in_deck("Village Green", 2)),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 3)),
            PriorityRule("Silver", PriorityRule.turn_number("<=", 4)),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
        ]

        self.action_priority = [
            PriorityRule("Village Green"),
            PriorityRule("Rice Broker"),
            PriorityRule("Patron", PriorityRule.excess_actions(">=", 1)),
            PriorityRule("Patron"),
        ]

        self.way_policy = [
            # Once there is nothing worth trashing, Rice Broker is a Lab.
            WayRule(
                "Rice Broker",
                "Way of the Otter",
                PriorityRule.has_no_cards(["Copper", "Estate"]),
            ),
            # Terminal-collision Patron is better as +2 Cards.
            WayRule(
                "Patron",
                "Way of the Otter",
                PriorityRule.excess_actions("<", 1),
            ),
        ]

        self.treasure_priority = [
            PriorityRule("Scepter"),
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Copper"),
        ]

        self.trash_priority = [
            PriorityRule("Estate", PriorityRule.provinces_left(">", 2)),
            PriorityRule("Copper"),
        ]


class HyderabadStockpileScholar(EnhancedStrategy):
    """Hybrid: Stockpile/Ducat buy economy with Scholar refills.

    Stockpile hands shrink as plays Exile the treasure; Scholar refills to
    seven regardless, and Progress topdecks each re-bought Stockpile for
    immediate redeployment. Ducat Coffers smooth the price points.
    """

    def __init__(self) -> None:
        super().__init__()
        self.name = "Hyderabad Stockpile Scholar"
        self.description = "Stockpile economy + Scholar draw hybrid."
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule("Province", PriorityRule.resources("coins", ">=", 8)),
            PriorityRule("Scholar", PriorityRule.max_in_deck("Scholar", 2)),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 5)),
            PriorityRule("Gold"),
            PriorityRule("Stockpile"),
            PriorityRule("Ducat"),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 3)),
        ]

        self.action_priority = [
            PriorityRule("Scholar", PriorityRule.treasures_in_hand("<=", 3)),
        ]

        self.treasure_priority = [
            PriorityRule("Stockpile"),
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Ducat"),
            PriorityRule("Copper"),
        ]


class HyderabadPriestStockpile(EnhancedStrategy):
    """Hybrid: Priest thinning into a Stockpile/Ducat buy engine.

    Priest strips the starting junk (each extra trash pays $2 on the way),
    then recurring Stockpiles plus Coffers buy green on multiple buys a
    turn while the Stockpile pile drains toward three piles.
    """

    def __init__(self) -> None:
        super().__init__()
        self.name = "Hyderabad Priest Stockpile"
        self.description = "Priest thinning + Stockpile/Ducat buy economy."
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule("Province", PriorityRule.resources("coins", ">=", 8)),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 5)),
            PriorityRule("Priest", PriorityRule.max_in_deck("Priest", 1)),
            PriorityRule("Gold"),
            PriorityRule("Stockpile"),
            PriorityRule("Ducat"),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 3)),
        ]

        self.action_priority = [
            PriorityRule("Priest"),
        ]

        self.treasure_priority = [
            PriorityRule("Stockpile"),
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Ducat"),
            PriorityRule("Copper"),
        ]

        self.trash_priority = [
            PriorityRule("Estate", PriorityRule.provinces_left(">", 2)),
            PriorityRule("Copper", PriorityRule.has_cards(["Stockpile", "Silver", "Gold"], 3)),
        ]


def create_hyderabad_scholar_money() -> EnhancedStrategy:
    return HyderabadScholarMoney()


def create_hyderabad_stockpile_scholar() -> EnhancedStrategy:
    return HyderabadStockpileScholar()


def create_hyderabad_priest_stockpile() -> EnhancedStrategy:
    return HyderabadPriestStockpile()


def create_hyderabad_green_scholar_engine() -> EnhancedStrategy:
    return HyderabadGreenScholarEngine()


def create_hyderabad_priest_payload() -> EnhancedStrategy:
    return HyderabadPriestPayload()


def create_hyderabad_stockpile_rush() -> EnhancedStrategy:
    return HyderabadStockpileRush()


def create_hyderabad_otter_broker_engine() -> EnhancedStrategy:
    return HyderabadOtterBrokerEngine()

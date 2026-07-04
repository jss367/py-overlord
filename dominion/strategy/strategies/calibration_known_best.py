"""Known-best archetype strategies for the calibration suite.

Each strategy encodes a community-known best (or near-best) plan for one of
the boards in ``boards/calibration/``. They are deliberately simple, clean
implementations of well-established archetypes — the point is to be a
trustworthy external reference for the evolution pipeline, not to squeeze
out the last percentage point.

See ``dominion/analysis/calibration.py`` for the board pairings and
``docs/calibration.md`` for sources.
"""

from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


def _greening_rules() -> list[PriorityRule]:
    """Standard Big-Money-style greening: Province, then late Duchy/Estate."""
    return [
        PriorityRule("Province"),
        PriorityRule("Duchy", PriorityRule.provinces_left("<=", 4)),
        PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
    ]


class DoubleSmithy(EnhancedStrategy):
    """Big Money plus two Smithies — the classic BM+X benchmark."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "Double Smithy"
        self.description = "Big Money with two Smithies and late greening"
        self.version = "1.0"

        self.gain_priority = _greening_rules() + [
            PriorityRule("Gold"),
            PriorityRule("Smithy", PriorityRule.max_in_deck("Smithy", 2)),
            PriorityRule("Silver"),
        ]
        self.action_priority = [PriorityRule("Smithy")]
        self.treasure_priority = [
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Copper"),
        ]


class DoubleWitch(EnhancedStrategy):
    """Big Money plus two Witches — curse pressure wins support-free boards."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "Double Witch"
        self.description = "Big Money with two Witches and late greening"
        self.version = "1.0"

        self.gain_priority = _greening_rules() + [
            PriorityRule("Witch", PriorityRule.max_in_deck("Witch", 2)),
            PriorityRule("Gold"),
            PriorityRule("Silver"),
        ]
        self.action_priority = [PriorityRule("Witch")]
        self.treasure_priority = [
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Copper"),
        ]


class ChapelWitchClassic(EnhancedStrategy):
    """Open Chapel, thin hard, add Witches, then money and green."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "Chapel Witch Classic"
        self.description = "Chapel thinning into double Witch money"
        self.version = "1.0"

        self.gain_priority = _greening_rules() + [
            PriorityRule("Witch", PriorityRule.max_in_deck("Witch", 2)),
            PriorityRule("Gold"),
            PriorityRule(
                "Chapel",
                PriorityRule.and_(
                    PriorityRule.max_in_deck("Chapel", 1),
                    PriorityRule.turn_number("<=", 3),
                ),
            ),
            PriorityRule("Silver"),
        ]
        self.action_priority = [
            PriorityRule("Witch"),
            PriorityRule(
                "Chapel",
                lambda _s, me: me.count_in_deck("Curse") > 0
                or me.count_in_deck("Estate") > 0
                or me.count_in_deck("Copper") > 4,
            ),
        ]
        self.trash_priority = [
            PriorityRule("Curse"),
            PriorityRule("Estate", PriorityRule.provinces_left(">", 2)),
            PriorityRule(
                "Copper",
                PriorityRule.has_cards(["Silver", "Gold"], 2),
            ),
        ]
        self.treasure_priority = [
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Copper"),
        ]


class GardensWorkshopRush(EnhancedStrategy):
    """Workshops gain Gardens every turn; fatten the deck and end on piles."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "Gardens Workshop Rush"
        self.description = "Workshop/Gardens rush with Copper fattening"
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule("Province"),
            PriorityRule("Gardens"),
            PriorityRule("Workshop", PriorityRule.max_in_deck("Workshop", 3)),
            PriorityRule("Estate", PriorityRule.empty_piles(">=", 1)),
            PriorityRule("Silver"),
            PriorityRule("Copper", PriorityRule.has_cards(["Gardens"], 3)),
        ]
        self.action_priority = [PriorityRule("Workshop")]
        self.treasure_priority = [
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Copper"),
        ]


class BigMoneyWharf(EnhancedStrategy):
    """Big Money plus two Wharves — the strongest classic BM+X."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "Big Money Wharf"
        self.description = "Big Money with two Wharves and late greening"
        self.version = "1.0"

        self.gain_priority = _greening_rules() + [
            PriorityRule("Gold"),
            PriorityRule("Wharf", PriorityRule.max_in_deck("Wharf", 2)),
            PriorityRule("Silver"),
        ]
        self.action_priority = [PriorityRule("Wharf")]
        self.treasure_priority = [
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Copper"),
        ]


class RebuildRush(EnhancedStrategy):
    """Two Rebuilds, Duchies over Gold, race the Province pile."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "Rebuild Rush"
        self.description = "Rebuild/Duchy rush — no Gold, Duchies become Provinces"
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule("Province"),
            PriorityRule("Rebuild", PriorityRule.max_in_deck("Rebuild", 2)),
            PriorityRule("Duchy"),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
            PriorityRule("Silver"),
        ]
        self.action_priority = [PriorityRule("Rebuild")]
        self.treasure_priority = [
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Copper"),
        ]


class DoubleJack(EnhancedStrategy):
    """Two Jacks of All Trades plus money — the Isotropic-era benchmark."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "Double Jack"
        self.description = "Big Money with two Jacks of All Trades"
        self.version = "1.0"

        self.gain_priority = _greening_rules() + [
            PriorityRule("Gold"),
            PriorityRule(
                "Jack of All Trades",
                PriorityRule.max_in_deck("Jack of All Trades", 2),
            ),
            PriorityRule("Silver"),
        ]
        self.action_priority = [PriorityRule("Jack of All Trades")]
        self.treasure_priority = [
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Copper"),
        ]


class MountebankMoney(EnhancedStrategy):
    """Big Money plus two Mountebanks — junk the opponent, buy points."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "Mountebank Money"
        self.description = "Big Money with two Mountebanks and late greening"
        self.version = "1.0"

        self.gain_priority = _greening_rules() + [
            PriorityRule("Mountebank", PriorityRule.max_in_deck("Mountebank", 2)),
            PriorityRule("Gold"),
            PriorityRule("Silver"),
        ]
        self.action_priority = [PriorityRule("Mountebank")]
        self.treasure_priority = [
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Copper"),
        ]


class CourtyardMoney(EnhancedStrategy):
    """Big Money plus two Courtyards bought on 2-4 coin hands."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "Courtyard Money"
        self.description = "Big Money with two cheap Courtyards"
        self.version = "1.0"

        self.gain_priority = _greening_rules() + [
            PriorityRule("Gold"),
            PriorityRule(
                "Courtyard",
                PriorityRule.and_(
                    PriorityRule.max_in_deck("Courtyard", 2),
                    PriorityRule.resources("coins", "<=", 4),
                ),
            ),
            PriorityRule("Silver"),
        ]
        self.action_priority = [PriorityRule("Courtyard")]
        self.treasure_priority = [
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Copper"),
        ]


class FirstGameSmithyMilitia(EnhancedStrategy):
    """Smithy money with a Militia on the base-set First Game kingdom."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "First Game Smithy Militia"
        self.description = "Smithy money plus one Militia for the First Game kingdom"
        self.version = "1.0"

        self.gain_priority = _greening_rules() + [
            PriorityRule("Gold"),
            PriorityRule("Smithy", PriorityRule.max_in_deck("Smithy", 2)),
            PriorityRule("Militia", PriorityRule.max_in_deck("Militia", 1)),
            PriorityRule("Silver"),
        ]
        self.action_priority = [
            PriorityRule("Smithy"),
            PriorityRule("Militia"),
        ]
        self.treasure_priority = [
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Copper"),
        ]


def create_double_smithy() -> EnhancedStrategy:
    return DoubleSmithy()


def create_double_witch() -> EnhancedStrategy:
    return DoubleWitch()


def create_chapel_witch_classic() -> EnhancedStrategy:
    return ChapelWitchClassic()


def create_gardens_workshop_rush() -> EnhancedStrategy:
    return GardensWorkshopRush()


def create_big_money_wharf() -> EnhancedStrategy:
    return BigMoneyWharf()


def create_rebuild_rush() -> EnhancedStrategy:
    return RebuildRush()


def create_double_jack() -> EnhancedStrategy:
    return DoubleJack()


def create_mountebank_money() -> EnhancedStrategy:
    return MountebankMoney()


def create_courtyard_money() -> EnhancedStrategy:
    return CourtyardMoney()


def create_first_game_smithy_militia() -> EnhancedStrategy:
    return FirstGameSmithyMilitia()

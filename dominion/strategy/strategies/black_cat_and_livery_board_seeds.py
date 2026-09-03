"""Island seeds for the Black Cat and Livery board.

See ``boards/black_cat_and_livery.txt`` for the full setup.

Kingdom: Black Cat, Stockpile, Infirmary, Bounty Hunter, Cardinal, Cavalry,
Barge, Journeyman, Livery, Fisherman — with Way of the Ox and the Invest
event. No Colony/Platinum.

Board texture
-------------
- There is no village, but Way of the Ox turns *any* Action into +2
  Actions. Black Cat ($2) and Horses ($0, from Cavalry and Livery) are the
  cheapest Ox fodder, so an engine here is "cheap Actions as villages,
  Barge/Journeyman for draw, Livery/Bounty Hunter for money".
- Livery is terminal +$3 that gains a Horse for every $4+ gain that turn:
  Gold, Duchy, Province and every $5 all feed Horses back into the deck.
- Buying Cavalry mid-turn draws 2, gives +1 Buy and re-opens the Action
  phase (with the Actions you have left), and Cavalry played gains 2
  Horses.
- Bounty Hunter is non-terminal thinning that pays $3 the first time each
  card name is Exiled; Infirmary is a cantrip trasher whose overpay plays
  it again per $1.
- Stockpile is $3 +Buy that Exiles itself, and every Stockpile bought later
  returns the Exiled ones to the deck.
- Black Cat in hand on the opponent's turn hands out a Curse whenever they
  gain green; Cardinal Exiles their $3-$6 cards off the top of the deck.

Each seed is a distinct theory of the kingdom for the island model.
"""

from dominion.strategy.enhanced_strategy import (
    EnhancedStrategy,
    PriorityRule,
    WayRule,
)


def _junk_in_hand():
    return PriorityRule.or_(
        PriorityRule.card_in_hand("Copper"),
        PriorityRule.card_in_hand("Estate"),
        PriorityRule.card_in_hand("Curse"),
    )


def _terminal_collision():
    """True when there are more terminals in hand than Actions to play them."""
    return PriorityRule.excess_actions("<", 0)


def _ox_villages(*cards: str) -> list[WayRule]:
    """Play the named cards as Way of the Ox when terminals collide."""
    return [WayRule(card, "Way of the Ox", _terminal_collision()) for card in cards]


_TREASURES = [
    PriorityRule("Gold"),
    PriorityRule("Silver"),
    PriorityRule("Copper"),
    # Stockpile Exiles itself, so only cash it when the hand is short of a
    # Province (it comes back whenever another Stockpile is bought).
    PriorityRule("Stockpile", PriorityRule.resources("coins", "<", 8)),
]


class BlackCatAndLiveryBoardLiveryMoney(EnhancedStrategy):
    """Big Money with Livery payload and one Journeyman.

    Every Gold/Province bought with Livery in play gains a Horse, so the
    money deck picks up free Labs as it greens.
    """

    def __init__(self) -> None:
        super().__init__()
        self.name = "Black Cat and Livery Board: Livery Money"
        self.description = "Money + Livery ($3, Horses on $4+ gains) + Journeyman."
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule("Province", PriorityRule.resources("coins", ">=", 8)),
            PriorityRule("Gold"),
            PriorityRule("Livery", PriorityRule.max_in_deck("Livery", 2)),
            PriorityRule("Journeyman", PriorityRule.max_in_deck("Journeyman", 1)),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 4)),
            PriorityRule("Silver"),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
        ]
        self.action_priority = [
            PriorityRule("Horse"),
            PriorityRule("Journeyman"),
            PriorityRule("Livery"),
        ]
        self.way_policy = _ox_villages("Horse")
        self.treasure_priority = list(_TREASURES)


class BlackCatAndLiveryBoardBountyStockpile(EnhancedStrategy):
    """Bounty Hunter thinning into a Stockpile +Buy money rush.

    Bounty Hunter pays $3 the first time each junk name is Exiled and keeps
    thinning after that; Stockpile gives $3 +Buy for $3 and drains its own
    pile toward a three-pile ending.
    """

    def __init__(self) -> None:
        super().__init__()
        self.name = "Black Cat and Livery Board: Bounty Hunter and Stockpile"
        self.description = "Bounty Hunter thinning + Stockpile +Buy money."
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule("Province", PriorityRule.resources("coins", ">=", 8)),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 5)),
            PriorityRule("Bounty Hunter", PriorityRule.max_in_deck("Bounty Hunter", 2)),
            PriorityRule("Gold"),
            PriorityRule("Stockpile"),
            PriorityRule("Silver"),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 3)),
        ]
        self.action_priority = [
            PriorityRule("Bounty Hunter", _junk_in_hand()),
        ]
        self.treasure_priority = [
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Copper"),
            PriorityRule("Stockpile"),
        ]


class BlackCatAndLiveryBoardCardinalCatMoney(EnhancedStrategy):
    """Attack money: two Cardinals plus Black Cats to punish greening.

    Cardinal is terminal $2 that Exiles the opponent's $3-$6 cards off the
    top of their deck; Black Cat draws 2 on your turn and Curses them
    whenever they gain green while it sits in your hand.
    """

    def __init__(self) -> None:
        super().__init__()
        self.name = "Black Cat and Livery Board: Cardinal and Black Cat Money"
        self.description = "Money + Cardinal attacks + Black Cat reactions."
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule("Province", PriorityRule.resources("coins", ">=", 8)),
            PriorityRule("Gold"),
            PriorityRule("Cardinal", PriorityRule.max_in_deck("Cardinal", 2)),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 4)),
            PriorityRule("Black Cat", PriorityRule.max_in_deck("Black Cat", 2)),
            PriorityRule("Silver"),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
        ]
        self.action_priority = [
            PriorityRule("Black Cat", _terminal_collision()),
            PriorityRule("Cardinal"),
            PriorityRule("Black Cat"),
        ]
        self.way_policy = _ox_villages("Black Cat")
        self.treasure_priority = list(_TREASURES)


class BlackCatAndLiveryBoardOxEngine(EnhancedStrategy):
    """Ox engine: Black Cats and Horses as villages, Barge/Journeyman draw,
    Livery and Bounty Hunter for money, Stockpile for +Buy.

    Way of the Ox turns the $2 Black Cat into a village on demand; Livery
    turns every $4+ gain into a Horse that is both a Lab and another
    village.
    """

    def __init__(self) -> None:
        super().__init__()
        self.name = "Black Cat and Livery Board: Way of the Ox Engine"
        self.description = (
            "Black Cat/Horse Ox villages, Barge+Journeyman draw, Livery payload."
        )
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule("Province", PriorityRule.resources("coins", ">=", 8)),
            PriorityRule("Gold", PriorityRule.max_in_deck("Gold", 2)),
            PriorityRule("Livery", PriorityRule.max_in_deck("Livery", 2)),
            PriorityRule("Barge", PriorityRule.max_in_deck("Barge", 2)),
            PriorityRule("Journeyman", PriorityRule.max_in_deck("Journeyman", 1)),
            PriorityRule("Gold"),
            PriorityRule("Bounty Hunter", PriorityRule.and_(
                PriorityRule.max_in_deck("Bounty Hunter", 1),
                PriorityRule.turn_number("<=", 6),
            )),
            PriorityRule("Fisherman", PriorityRule.max_in_deck("Fisherman", 2)),
            PriorityRule("Cavalry", PriorityRule.and_(
                PriorityRule.max_in_deck("Cavalry", 1),
                PriorityRule.has_cards(["Livery"], 1),
            )),
            PriorityRule("Silver", PriorityRule.max_in_deck("Silver", 3)),
            PriorityRule("Stockpile", PriorityRule.max_in_deck("Stockpile", 2)),
            PriorityRule("Black Cat", PriorityRule.and_(
                PriorityRule.max_in_deck("Black Cat", 3),
                PriorityRule.has_cards(["Barge", "Journeyman", "Livery"], 2),
            )),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 3)),
            PriorityRule("Silver"),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
        ]
        self.action_priority = [
            PriorityRule("Horse", _terminal_collision()),
            PriorityRule("Black Cat", _terminal_collision()),
            PriorityRule("Horse"),
            PriorityRule("Bounty Hunter", _junk_in_hand()),
            PriorityRule("Fisherman"),
            PriorityRule("Barge"),
            PriorityRule("Journeyman"),
            PriorityRule("Black Cat"),
            PriorityRule("Livery"),
            PriorityRule("Cavalry"),
            PriorityRule("Cardinal"),
            PriorityRule("Infirmary"),
        ]
        self.way_policy = _ox_villages("Horse", "Black Cat", "Infirmary", "Cardinal")
        self.treasure_priority = list(_TREASURES)
        self.trash_priority = [
            PriorityRule("Curse"),
            PriorityRule("Estate", PriorityRule.provinces_left(">", 2)),
            PriorityRule("Copper", PriorityRule.has_cards(["Silver", "Gold", "Livery", "Bounty Hunter"], 3)),
        ]


class BlackCatAndLiveryBoardFishermanInfirmary(EnhancedStrategy):
    """Thin peddler deck: Infirmary trashes, Fisherman peddlers, Barge draw.

    Infirmary's overpay plays it again per $1, so an early $5 hand buys a
    multi-trash; once thin, Fishermen and Barges cycle the deck every turn.
    """

    def __init__(self) -> None:
        super().__init__()
        self.name = "Black Cat and Livery Board: Fisherman and Infirmary Engine"
        self.description = "Infirmary thinning into Fisherman peddlers + Barge draw."
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule("Province", PriorityRule.resources("coins", ">=", 8)),
            PriorityRule("Infirmary", PriorityRule.and_(
                PriorityRule.max_in_deck("Infirmary", 1),
                PriorityRule.turn_number("<=", 4),
            )),
            PriorityRule("Barge", PriorityRule.max_in_deck("Barge", 2)),
            PriorityRule("Livery", PriorityRule.max_in_deck("Livery", 1)),
            PriorityRule("Fisherman", PriorityRule.max_in_deck("Fisherman", 4)),
            PriorityRule("Bounty Hunter", PriorityRule.max_in_deck("Bounty Hunter", 1)),
            PriorityRule("Gold"),
            PriorityRule("Black Cat", PriorityRule.max_in_deck("Black Cat", 2)),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 3)),
            PriorityRule("Silver", PriorityRule.turn_number("<=", 3)),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
        ]
        self.action_priority = [
            PriorityRule("Horse", _terminal_collision()),
            PriorityRule("Black Cat", _terminal_collision()),
            PriorityRule("Horse"),
            PriorityRule("Fisherman"),
            PriorityRule("Bounty Hunter", _junk_in_hand()),
            PriorityRule("Infirmary", _junk_in_hand()),
            PriorityRule("Barge"),
            PriorityRule("Black Cat"),
            PriorityRule("Livery"),
            PriorityRule("Infirmary"),
        ]
        self.way_policy = _ox_villages("Horse", "Black Cat", "Infirmary")
        self.treasure_priority = list(_TREASURES)
        self.trash_priority = [
            PriorityRule("Curse"),
            PriorityRule("Estate", PriorityRule.provinces_left(">", 2)),
            PriorityRule("Copper", PriorityRule.has_cards(["Silver", "Gold", "Fisherman", "Livery"], 3)),
        ]


class BlackCatAndLiveryBoardCavalryHorses(EnhancedStrategy):
    """Horse engine: Livery + Cavalry flood the deck with Horses.

    Cavalry played gains 2 Horses; Cavalry bought with Livery in play gains
    a Horse, draws 2 and re-opens the Action phase. Horses are Labs, or
    villages via Way of the Ox when terminals collide.
    """

    def __init__(self) -> None:
        super().__init__()
        self.name = "Black Cat and Livery Board: Cavalry Horse Engine"
        self.description = "Livery + Cavalry Horse flood with Barge draw."
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule("Province", PriorityRule.resources("coins", ">=", 8)),
            PriorityRule("Gold", PriorityRule.max_in_deck("Gold", 2)),
            PriorityRule("Livery", PriorityRule.max_in_deck("Livery", 2)),
            PriorityRule("Barge", PriorityRule.max_in_deck("Barge", 2)),
            PriorityRule("Gold"),
            PriorityRule("Cavalry", PriorityRule.and_(
                PriorityRule.max_in_deck("Cavalry", 2),
                PriorityRule.has_cards(["Livery"], 1),
            )),
            PriorityRule("Silver", PriorityRule.max_in_deck("Silver", 3)),
            PriorityRule("Stockpile", PriorityRule.max_in_deck("Stockpile", 2)),
            PriorityRule("Black Cat", PriorityRule.and_(
                PriorityRule.max_in_deck("Black Cat", 2),
                PriorityRule.has_cards(["Livery", "Barge"], 2),
            )),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 3)),
            PriorityRule("Silver"),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
        ]
        self.action_priority = [
            PriorityRule("Horse", _terminal_collision()),
            PriorityRule("Black Cat", _terminal_collision()),
            PriorityRule("Horse"),
            PriorityRule("Barge"),
            PriorityRule("Cavalry"),
            PriorityRule("Livery"),
            PriorityRule("Black Cat"),
        ]
        self.way_policy = _ox_villages("Horse", "Black Cat", "Cavalry")
        self.treasure_priority = list(_TREASURES)


def create_black_cat_and_livery_board_livery_money() -> EnhancedStrategy:
    return BlackCatAndLiveryBoardLiveryMoney()


def create_black_cat_and_livery_board_bounty_stockpile() -> EnhancedStrategy:
    return BlackCatAndLiveryBoardBountyStockpile()


def create_black_cat_and_livery_board_cardinal_cat_money() -> EnhancedStrategy:
    return BlackCatAndLiveryBoardCardinalCatMoney()


def create_black_cat_and_livery_board_ox_engine() -> EnhancedStrategy:
    return BlackCatAndLiveryBoardOxEngine()


def create_black_cat_and_livery_board_fisherman_infirmary() -> EnhancedStrategy:
    return BlackCatAndLiveryBoardFishermanInfirmary()


def create_black_cat_and_livery_board_cavalry_horses() -> EnhancedStrategy:
    return BlackCatAndLiveryBoardCavalryHorses()

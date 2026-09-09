"""Island seeds for the Kolkata board (``boards/kolkata.txt``).

Kingdom: Artist (8 Debt), Artificer, Armory, Bandit Camp, Bard, Knights,
Research, Scheme, Spice Merchant, Stables. No events or landmarks.

Board texture
-------------
- Bandit Camp is the only village: +1 Card +2 Actions and a Spoils ($3
  one-shot Treasure that returns to its pile when played).
- Stables is the draw: discard a Treasure for +3 Cards +1 Action. Spoils
  and Coppers are Stables fuel, so the deck wants to keep some Treasure.
- Artist (8 Debt) is +1 Action and +1 Card per card you have exactly one
  copy of in play, so it rewards variety rather than duplicates.
- Knights are the only attack: each play trashes one of the opponent's top
  two cards costing $3-$6 (Silver, Gold, every kingdom card, Duchy). Only
  Dame Sylvia gives +$2; Sir Martin costs $4 and gives +2 Buys.
- Trashing: Research (trash a card, draw its cost next turn), Spice
  Merchant (trash a Treasure for +2 Cards +1 Action or +$2 +1 Buy) and
  Dame Anna.
- Gainers: Armory (a $4 onto the deck), Artificer (discard N cards, gain a
  $N card onto the deck), Dame Natalie ($3).
- Scheme topdecks one Action at Clean-up: a Knight attacks every turn.
- Bard is +$2 and a Boon. Extra Buys come from Spice Merchant, Sir Martin,
  and Bard's Boon when it is The Forest's Gift (+1 Buy +$1).

Each seed below is a distinct theory of the kingdom for the island model.
``"Knights"`` in a rule matches whichever Knight is on top of the pile.
"""

from dominion.strategy.enhanced_strategy import (
    EnhancedStrategy,
    PriorityRule,
)


def _treasures() -> list[PriorityRule]:
    return [
        PriorityRule("Gold"),
        PriorityRule("Spoils"),
        PriorityRule("Silver"),
        PriorityRule("Copper"),
    ]


def _greening(duchy_at: int = 4, estate_at: int = 2) -> list[PriorityRule]:
    return [
        PriorityRule("Province"),
        PriorityRule("Duchy", PriorityRule.provinces_left("<=", duchy_at)),
        PriorityRule("Estate", PriorityRule.provinces_left("<=", estate_at)),
    ]


def _junk_trash(include_copper: bool = False) -> list[PriorityRule]:
    rules = [PriorityRule("Curse"), PriorityRule("Estate")]
    if include_copper:
        rules.append(PriorityRule("Copper"))
    return rules


class KolkataKnightsMoney(EnhancedStrategy):
    """Big Money with two Knights."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "Kolkata Knights Money"
        self.description = "Big Money plus two Knights; nothing else."
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule("Province"),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 4)),
            PriorityRule("Gold"),
            PriorityRule("Knights", PriorityRule.max_in_deck("Knights", 2)),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
            PriorityRule("Silver"),
        ]
        self.action_priority = [PriorityRule("Knights")]
        self.trash_priority = _junk_trash()
        self.treasure_priority = _treasures()


class KolkataSchemeKnightsMoney(EnhancedStrategy):
    """Money with two Knights and a Scheme so a Knight attacks every turn."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "Kolkata Scheme Knights Money"
        self.description = "Two Knights, one Scheme to topdeck a Knight each turn, money."
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule("Province"),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 4)),
            PriorityRule("Gold"),
            PriorityRule("Knights", PriorityRule.max_in_deck("Knights", 2)),
            PriorityRule(
                "Scheme",
                PriorityRule.and_(
                    PriorityRule.max_in_deck("Scheme", 1),
                    PriorityRule.has_cards(["Knights"], 1),
                ),
            ),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
            PriorityRule("Silver"),
        ]
        self.action_priority = [PriorityRule("Scheme"), PriorityRule("Knights")]
        self.trash_priority = _junk_trash()
        self.treasure_priority = _treasures()

    def choose_card_to_topdeck_for_scheme(self, state, player, choices):
        """Put a Knight on the deck when one was played; otherwise nothing."""
        knight = next((c for c in choices if c.is_knight), None)
        return knight


class KolkataStablesMoney(EnhancedStrategy):
    """Big Money with Stables draw (discard Copper for three cards)."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "Kolkata Stables Money"
        self.description = "Money with two Stables and a Knight."
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule("Province"),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 4)),
            PriorityRule("Gold"),
            PriorityRule("Stables", PriorityRule.max_in_deck("Stables", 2)),
            PriorityRule("Knights", PriorityRule.max_in_deck("Knights", 1)),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
            PriorityRule("Silver"),
        ]
        self.action_priority = [PriorityRule("Stables"), PriorityRule("Knights")]
        self.trash_priority = _junk_trash()
        self.treasure_priority = _treasures()


class KolkataBardMoney(EnhancedStrategy):
    """Big Money with two Bards (+$2 and a Boon each)."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "Kolkata Bard Money"
        self.description = "Money with two Bards."
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule("Province"),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 4)),
            PriorityRule("Gold"),
            PriorityRule("Bard", PriorityRule.max_in_deck("Bard", 2)),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
            PriorityRule("Silver"),
        ]
        self.action_priority = [PriorityRule("Bard")]
        self.trash_priority = _junk_trash()
        self.treasure_priority = _treasures()


class KolkataSpiceMerchantMoney(EnhancedStrategy):
    """Money that thins Coppers with Spice Merchant, plus a Knight."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "Kolkata Spice Merchant Money"
        self.description = "Spice Merchant Copper trashing, one Knight, money."
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule("Province"),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 4)),
            PriorityRule("Gold"),
            PriorityRule("Knights", PriorityRule.max_in_deck("Knights", 1)),
            PriorityRule(
                "Spice Merchant",
                PriorityRule.and_(
                    PriorityRule.max_in_deck("Spice Merchant", 1),
                    PriorityRule.turn_number("<=", 6),
                ),
            ),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
            PriorityRule("Silver"),
        ]
        self.action_priority = [PriorityRule("Spice Merchant"), PriorityRule("Knights")]
        self.trash_priority = _junk_trash(include_copper=True)
        self.treasure_priority = _treasures()


class KolkataArmoryBardMoney(EnhancedStrategy):
    """Armory gains Bards and Silvers onto the deck for a money deck."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "Kolkata Armory Bard Money"
        self.description = "Armory topdecks Bards then Silvers; money."
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule("Province"),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 4)),
            PriorityRule("Gold"),
            PriorityRule("Bard", PriorityRule.max_in_deck("Bard", 2)),
            PriorityRule(
                "Armory",
                PriorityRule.and_(
                    PriorityRule.max_in_deck("Armory", 1),
                    PriorityRule.turn_number("<=", 6),
                ),
            ),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
            PriorityRule("Silver"),
        ]
        self.action_priority = [PriorityRule("Armory"), PriorityRule("Bard")]
        self.trash_priority = _junk_trash()
        self.treasure_priority = _treasures()


class KolkataBanditCampStablesEngine(EnhancedStrategy):
    """Bandit Camp / Stables engine: Spoils fuel Stables, Knights attack.

    Bandit Camps make Spoils and Actions, Stables discards a Copper or a
    Spoils to draw three, and two Knights (one topdecked by Scheme) trash
    the opponent's Silvers, Golds and kingdom cards. The deck keeps its
    Coppers and buys Silver and Gold: every Treasure is Stables fuel.
    """

    def __init__(self) -> None:
        super().__init__()
        self.name = "Kolkata Bandit Camp Stables Engine"
        self.description = "Bandit Camp village, Stables draw, Knights attack, Spoils payload."
        self.version = "1.1"

        self.gain_priority = [
            PriorityRule("Province", PriorityRule.resources("coins", ">=", 8)),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 3)),
            PriorityRule("Gold", PriorityRule.max_in_deck("Gold", 2)),
            PriorityRule("Stables", PriorityRule.max_in_deck("Stables", 1)),
            PriorityRule(
                "Bandit Camp",
                PriorityRule.and_(
                    PriorityRule.max_in_deck("Bandit Camp", 3),
                    PriorityRule.has_cards(["Stables"], 1),
                ),
            ),
            PriorityRule("Knights", PriorityRule.max_in_deck("Knights", 2)),
            PriorityRule("Stables", PriorityRule.max_in_deck("Stables", 4)),
            PriorityRule("Gold"),
            PriorityRule(
                "Scheme",
                PriorityRule.and_(
                    PriorityRule.max_in_deck("Scheme", 1),
                    PriorityRule.has_cards(["Knights"], 1),
                ),
            ),
            PriorityRule("Silver"),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
        ]
        self.action_priority = [
            PriorityRule("Bandit Camp"),
            PriorityRule("Scheme"),
            PriorityRule("Stables"),
            PriorityRule("Knights"),
        ]
        self.trash_priority = _junk_trash()
        self.treasure_priority = _treasures()

    def choose_card_to_topdeck_for_scheme(self, state, player, choices):
        """Put a Knight on the deck when one was played, else a Stables, else nothing."""
        knight = next((c for c in choices if c.is_knight), None)
        if knight is not None:
            return knight
        return next((c for c in choices if c.name == "Stables"), None)


class KolkataArtificerEngine(EnhancedStrategy):
    """Bandit Camp / Stables engine that uses Artificer to gain $5s onto the deck.

    Artificer discards the junk drawn by Stables (Coppers, Estates) to put
    a Stables or a Bandit Camp on top of the deck, where the next Stables
    draws it.
    """

    def __init__(self) -> None:
        super().__init__()
        self.name = "Kolkata Artificer Engine"
        self.description = "Bandit Camp, Stables, and Artificer gaining $5s onto the deck."
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule("Province", PriorityRule.resources("coins", ">=", 8)),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 3)),
            PriorityRule("Gold", PriorityRule.max_in_deck("Gold", 1)),
            PriorityRule("Stables", PriorityRule.max_in_deck("Stables", 1)),
            PriorityRule(
                "Bandit Camp",
                PriorityRule.and_(
                    PriorityRule.max_in_deck("Bandit Camp", 3),
                    PriorityRule.has_cards(["Stables"], 1),
                ),
            ),
            PriorityRule("Stables", PriorityRule.max_in_deck("Stables", 4)),
            PriorityRule("Artificer", PriorityRule.max_in_deck("Artificer", 2)),
            PriorityRule("Knights", PriorityRule.max_in_deck("Knights", 1)),
            PriorityRule("Gold"),
            PriorityRule("Bard", PriorityRule.max_in_deck("Bard", 1)),
            PriorityRule("Silver"),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
        ]
        self.action_priority = [
            PriorityRule("Bandit Camp"),
            PriorityRule("Stables"),
            PriorityRule("Artificer"),
            PriorityRule("Knights"),
            PriorityRule("Bard"),
        ]
        self.trash_priority = _junk_trash()
        self.treasure_priority = _treasures()

    def choose_artificer_gain(self, state, player, choices):
        """Only discard junk (Coppers, Curses, Victory cards): gain the best card
        from the gain list whose cost the junk in hand can pay, never a $0 card."""
        junk = [
            c
            for c in player.hand
            if c.name in {"Copper", "Curse"} or (c.is_victory and not c.is_action)
        ]
        affordable = [c for c in choices if 0 < c.cost.coins <= len(junk)]
        if not affordable:
            return None
        return self.choose_gain(state, player, affordable + [None])


class KolkataArtistEngine(EnhancedStrategy):
    """Variety engine: one of everything so Artist draws the deck.

    Artist (8 Debt) draws a card per singleton in play, so the deck keeps
    one Bandit Camp, Stables, Scheme, Research, Spice Merchant, Bard,
    Knight and Artificer in play and adds Artist once the singletons exist.
    """

    def __init__(self) -> None:
        super().__init__()
        self.name = "Kolkata Artist Engine"
        self.description = "Singleton engine with Artist draw and Bandit Camp actions."
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule("Province", PriorityRule.resources("coins", ">=", 8)),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 3)),
            PriorityRule(
                "Artist",
                PriorityRule.and_(
                    PriorityRule.max_in_deck("Artist", 1),
                    PriorityRule.has_cards(["Bandit Camp"], 2),
                    PriorityRule.has_cards(["Stables"], 1),
                ),
            ),
            PriorityRule("Gold", PriorityRule.max_in_deck("Gold", 1)),
            PriorityRule("Bandit Camp", PriorityRule.max_in_deck("Bandit Camp", 3)),
            PriorityRule("Stables", PriorityRule.max_in_deck("Stables", 2)),
            PriorityRule("Knights", PriorityRule.max_in_deck("Knights", 2)),
            PriorityRule("Gold"),
            PriorityRule("Artificer", PriorityRule.max_in_deck("Artificer", 1)),
            PriorityRule("Bard", PriorityRule.max_in_deck("Bard", 1)),
            PriorityRule("Spice Merchant", PriorityRule.max_in_deck("Spice Merchant", 1)),
            PriorityRule("Research", PriorityRule.max_in_deck("Research", 1)),
            PriorityRule("Scheme", PriorityRule.max_in_deck("Scheme", 1)),
            PriorityRule("Silver"),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
        ]
        self.action_priority = [
            PriorityRule("Bandit Camp"),
            PriorityRule("Scheme"),
            PriorityRule("Artist"),
            PriorityRule("Stables"),
            PriorityRule("Research"),
            PriorityRule("Artificer"),
            PriorityRule("Spice Merchant"),
            PriorityRule("Knights"),
            PriorityRule("Bard"),
        ]
        self.trash_priority = _junk_trash()
        self.treasure_priority = _treasures()


class KolkataResearchEngine(EnhancedStrategy):
    """Research thins Estates (and later Silvers) into next-turn draw.

    Bandit Camp for Actions and Spoils, Stables for draw, Research trashing
    Estates for two cards each next turn, Knights on top.
    """

    def __init__(self) -> None:
        super().__init__()
        self.name = "Kolkata Research Engine"
        self.description = "Research thinning, Bandit Camp, Stables, Knights."
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule("Province", PriorityRule.resources("coins", ">=", 8)),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 3)),
            PriorityRule(
                "Research",
                PriorityRule.and_(
                    PriorityRule.max_in_deck("Research", 2),
                    PriorityRule.turn_number("<=", 8),
                ),
            ),
            PriorityRule("Gold", PriorityRule.max_in_deck("Gold", 2)),
            PriorityRule("Stables", PriorityRule.max_in_deck("Stables", 1)),
            PriorityRule(
                "Bandit Camp",
                PriorityRule.and_(
                    PriorityRule.max_in_deck("Bandit Camp", 3),
                    PriorityRule.has_cards(["Stables"], 1),
                ),
            ),
            PriorityRule("Stables", PriorityRule.max_in_deck("Stables", 3)),
            PriorityRule("Knights", PriorityRule.max_in_deck("Knights", 2)),
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
        ]
        self.action_priority = [
            PriorityRule("Bandit Camp"),
            PriorityRule("Stables"),
            PriorityRule("Research"),
            PriorityRule("Knights"),
        ]
        self.trash_priority = [
            PriorityRule("Curse"),
            PriorityRule("Estate"),
            PriorityRule("Silver", PriorityRule.has_cards(["Gold"], 2)),
        ]
        self.treasure_priority = _treasures()


class KolkataBardStablesMoney(EnhancedStrategy):
    """Money with two Bards for payload and two Stables for draw."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "Kolkata Bard Stables Money"
        self.description = "Money with two Stables and two Bards."
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule("Province"),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 4)),
            PriorityRule("Gold"),
            PriorityRule("Stables", PriorityRule.max_in_deck("Stables", 2)),
            PriorityRule("Bard", PriorityRule.max_in_deck("Bard", 2)),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
            PriorityRule("Silver"),
        ]
        self.action_priority = [PriorityRule("Stables"), PriorityRule("Bard")]
        self.trash_priority = _junk_trash()
        self.treasure_priority = _treasures()


class KolkataStablesKnightsMoney(EnhancedStrategy):
    """Money with two Stables and two Knights."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "Kolkata Stables Knights Money"
        self.description = "Money with two Stables and two Knights."
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule("Province"),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 4)),
            PriorityRule("Gold"),
            PriorityRule("Stables", PriorityRule.max_in_deck("Stables", 2)),
            PriorityRule("Knights", PriorityRule.max_in_deck("Knights", 2)),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
            PriorityRule("Silver"),
        ]
        self.action_priority = [PriorityRule("Stables"), PriorityRule("Knights")]
        self.trash_priority = _junk_trash()
        self.treasure_priority = _treasures()


class KolkataBanditCampMoney(EnhancedStrategy):
    """Money with two Bandit Camps: each play banks a $3 Spoils."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "Kolkata Bandit Camp Money"
        self.description = "Money with two Bandit Camps (Spoils) and a Stables."
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule("Province"),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 4)),
            PriorityRule("Gold"),
            PriorityRule("Bandit Camp", PriorityRule.max_in_deck("Bandit Camp", 2)),
            PriorityRule("Stables", PriorityRule.max_in_deck("Stables", 1)),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
            PriorityRule("Silver"),
        ]
        self.action_priority = [PriorityRule("Bandit Camp"), PriorityRule("Stables")]
        self.trash_priority = _junk_trash()
        self.treasure_priority = _treasures()


def create_kolkata_knights_money() -> EnhancedStrategy:
    return KolkataKnightsMoney()


def create_kolkata_scheme_knights_money() -> EnhancedStrategy:
    return KolkataSchemeKnightsMoney()


def create_kolkata_stables_money() -> EnhancedStrategy:
    return KolkataStablesMoney()


def create_kolkata_bard_money() -> EnhancedStrategy:
    return KolkataBardMoney()


def create_kolkata_spice_merchant_money() -> EnhancedStrategy:
    return KolkataSpiceMerchantMoney()


def create_kolkata_armory_bard_money() -> EnhancedStrategy:
    return KolkataArmoryBardMoney()


def create_kolkata_bandit_camp_stables_engine() -> EnhancedStrategy:
    return KolkataBanditCampStablesEngine()


def create_kolkata_artificer_engine() -> EnhancedStrategy:
    return KolkataArtificerEngine()


def create_kolkata_artist_engine() -> EnhancedStrategy:
    return KolkataArtistEngine()


def create_kolkata_research_engine() -> EnhancedStrategy:
    return KolkataResearchEngine()


def create_kolkata_bard_stables_money() -> EnhancedStrategy:
    return KolkataBardStablesMoney()


def create_kolkata_stables_knights_money() -> EnhancedStrategy:
    return KolkataStablesKnightsMoney()


def create_kolkata_bandit_camp_money() -> EnhancedStrategy:
    return KolkataBanditCampMoney()

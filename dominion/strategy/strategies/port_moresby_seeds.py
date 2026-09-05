"""Island seeds for the Port Moresby board (``boards/port_moresby.txt``).

Kingdom: Daimyo, Secluded Shrine, Carpenter, Messenger, Swamp Shacks, Trail,
Barbarian, Falconer, Quartermaster, Sculptor — with the Seaway event and the
Fountain landmark. No Colony/Platinum.

Board texture
-------------
- Fountain pays 15 VP for holding 10+ Coppers. Every deck starts with 7, so
  three cheap Copper buys (or Sculptor gains) are worth 2.5 Provinces. That
  also means Coppers must never be trashed here.
- Trail is the glue: it is a cantrip that plays itself whenever it is gained,
  so every $4 gainer on the board (Falconer, Sculptor, Carpenter, Messenger,
  Quartermaster, Seaway) becomes "+1 Card +1 Action and add a Trail".
- Falconer reacts to any player gaining a 2-type card. Trail is Action-
  Reaction, so a Falconer gaining a Trail fires the next Falconer in hand;
  buying Barbarian / Falconer / Shrine / Quartermaster in the Buy phase
  fires every Falconer left in hand.
- Swamp Shacks is the only village and the only draw: +2 Actions and +1 Card
  per 3 cards in play. Cantrip Trails and permanently-in-play Quartermasters
  inflate that count.
- Daimyo (6 Debt) replays the next non-Command Action: double Swamp Shacks
  or double Barbarian.
- Barbarian is the payload and the only attack: +$2, trash the opponent's
  top card, and junk them with a Curse when it was a Copper/Estate.
- Quartermaster stays in play for the game: gain a $4 each turn (a Trail
  plays itself immediately, drawing a card at turn start) or take a banked
  Silver into hand.
- Buys are scarce: Messenger (+1 Buy) and Seaway's +1 Buy token are the
  only sources.

Each seed below is a distinct theory of the kingdom for the island model.
"""

from dominion.strategy.enhanced_strategy import (
    EnhancedStrategy,
    PriorityRule,
)


def _fountain_copper_rule() -> PriorityRule:
    """Buy/gain Copper while short of Fountain's 10 (only ever the last resort)."""
    return PriorityRule("Copper", PriorityRule.max_in_deck("Copper", 10))


def _money_treasures() -> list[PriorityRule]:
    return [
        PriorityRule("Gold"),
        PriorityRule("Silver"),
        PriorityRule("Copper"),
    ]


def _junk_trash() -> list[PriorityRule]:
    """Never trash Copper on this board (Fountain)."""
    return [
        PriorityRule("Curse"),
        PriorityRule("Estate"),
    ]


class PortMoresbyBarbarianMoney(EnhancedStrategy):
    """Big Money + two Barbarians, topping up Coppers for Fountain."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "Port Moresby Barbarian Money"
        self.description = "Big Money with two Barbarians; keep 10 Coppers for Fountain."
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule("Province"),
            PriorityRule("Gold"),
            PriorityRule("Barbarian", PriorityRule.max_in_deck("Barbarian", 2)),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 4)),
            PriorityRule("Silver"),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
            _fountain_copper_rule(),
        ]
        self.action_priority = [PriorityRule("Barbarian")]
        self.trash_priority = _junk_trash()
        self.treasure_priority = _money_treasures()


class PortMoresbyQuartermasterMoney(EnhancedStrategy):
    """Money with an early Quartermaster banking Silvers and a Barbarian."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "Port Moresby Quartermaster Money"
        self.description = "Quartermaster banks Silvers/Trails; Barbarian + money."
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule("Province"),
            PriorityRule("Quartermaster", PriorityRule.max_in_deck("Quartermaster", 1)),
            PriorityRule("Gold"),
            PriorityRule("Barbarian", PriorityRule.max_in_deck("Barbarian", 2)),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 4)),
            PriorityRule("Silver"),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
            _fountain_copper_rule(),
        ]
        self.action_priority = [
            PriorityRule("Quartermaster"),
            PriorityRule("Barbarian"),
        ]
        self.trash_priority = _junk_trash()
        self.treasure_priority = _money_treasures()


class PortMoresbyDoubleQuartermasterMoney(EnhancedStrategy):
    """Money with two Quartermasters (both stay in play) and one Barbarian."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "Port Moresby Double Quartermaster Money"
        self.description = "Two Quartermasters banking Silvers; one Barbarian; money."
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule("Province"),
            PriorityRule("Quartermaster", PriorityRule.max_in_deck("Quartermaster", 2)),
            PriorityRule("Gold"),
            PriorityRule("Barbarian", PriorityRule.max_in_deck("Barbarian", 1)),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 4)),
            PriorityRule("Silver"),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
            _fountain_copper_rule(),
        ]
        self.action_priority = [
            PriorityRule("Quartermaster"),
            PriorityRule("Barbarian"),
        ]
        self.trash_priority = _junk_trash()
        self.treasure_priority = _money_treasures()


class PortMoresbySculptorFountainRush(EnhancedStrategy):
    """Sculptor gains Coppers to hand (Villager + Fountain), then green early."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "Port Moresby Sculptor Fountain Rush"
        self.description = "Sculptor Copper gains for Fountain; Barbarian; early Duchies."
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule("Province"),
            PriorityRule("Gold"),
            PriorityRule("Sculptor", PriorityRule.max_in_deck("Sculptor", 2)),
            PriorityRule("Barbarian", PriorityRule.max_in_deck("Barbarian", 1)),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 5)),
            PriorityRule("Silver"),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
            _fountain_copper_rule(),
        ]
        self.action_priority = [
            PriorityRule("Sculptor"),
            PriorityRule("Barbarian"),
        ]
        self.trash_priority = _junk_trash()
        self.treasure_priority = _money_treasures()

    def choose_gain(self, state, player, choices):
        # Sculptor (Action phase gain): take a Copper to hand while short of
        # ten — it is +$1 now, +1 Villager, and a step toward Fountain.
        if getattr(state, "phase", None) == "action":
            copper = next((c for c in choices if c is not None and c.name == "Copper"), None)
            if copper is not None and player.count_in_deck("Copper") < 10:
                return copper
        return super().choose_gain(state, player, choices)


class PortMoresbyFalconerTrailEngine(EnhancedStrategy):
    """Falconer/Trail chain engine with Swamp Shacks draw and Barbarian payload.

    Falconers gain Trails to hand (each Trail plays itself and fires the next
    Falconer). Swamp Shacks turns the pile of cantrips in play into draw,
    Daimyo doubles a Shacks or a Barbarian, and the deck keeps all its
    Coppers for Fountain.
    """

    def __init__(self) -> None:
        super().__init__()
        self.name = "Port Moresby Falconer Trail Engine"
        self.description = "Falconer->Trail chains, Swamp Shacks draw, Daimyo, Barbarian payload."
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule("Province", PriorityRule.resources("coins", ">=", 8)),
            PriorityRule(
                "Daimyo",
                PriorityRule.and_(
                    PriorityRule.resources("coins", ">=", 6),
                    PriorityRule.max_in_deck("Daimyo", 1),
                    PriorityRule.has_cards(["Swamp Shacks"], 2),
                ),
            ),
            PriorityRule("Gold", PriorityRule.max_in_deck("Gold", 2)),
            PriorityRule("Barbarian", PriorityRule.max_in_deck("Barbarian", 2)),
            PriorityRule("Falconer", PriorityRule.max_in_deck("Falconer", 3)),
            PriorityRule("Quartermaster", PriorityRule.max_in_deck("Quartermaster", 1)),
            PriorityRule(
                "Swamp Shacks",
                PriorityRule.and_(
                    PriorityRule.max_in_deck("Swamp Shacks", 3),
                    PriorityRule.or_(
                        PriorityRule.has_cards(["Trail"], 2),
                        PriorityRule.has_cards(["Falconer"], 1),
                    ),
                ),
            ),
            PriorityRule("Trail", PriorityRule.max_in_deck("Trail", 8)),
            PriorityRule(
                "Secluded Shrine",
                PriorityRule.and_(
                    PriorityRule.max_in_deck("Secluded Shrine", 1),
                    PriorityRule.turn_number("<=", 4),
                ),
            ),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 3)),
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
            _fountain_copper_rule(),
        ]
        self.action_priority = [
            PriorityRule("Trail"),
            PriorityRule(
                "Daimyo",
                PriorityRule.or_(
                    PriorityRule.card_in_hand("Swamp Shacks"),
                    PriorityRule.card_in_hand("Barbarian"),
                ),
            ),
            PriorityRule("Quartermaster"),
            PriorityRule("Swamp Shacks"),
            PriorityRule("Falconer"),
            PriorityRule("Sculptor"),
            PriorityRule("Carpenter"),
            PriorityRule("Secluded Shrine"),
            PriorityRule("Barbarian"),
            PriorityRule("Messenger"),
            PriorityRule("Daimyo"),
        ]
        self.trash_priority = _junk_trash()
        self.treasure_priority = _money_treasures()

    def choose_gain(self, state, player, choices):
        # Action-phase gains (Falconer/Sculptor/Carpenter): take a Trail when
        # another Falconer is waiting in hand, so the gained Trail plays
        # itself and fires the next Falconer (the chain the seed is about).
        if getattr(state, "phase", None) == "action":
            trail = next((c for c in choices if c is not None and c.name == "Trail"), None)
            if trail is not None and any(c.name == "Falconer" for c in player.hand):
                return trail
        return super().choose_gain(state, player, choices)


class PortMoresbySwampDaimyoEngine(EnhancedStrategy):
    """Swamp Shacks/Daimyo draw engine on a money base, Trails from Sculptor."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "Port Moresby Swamp Daimyo Engine"
        self.description = "Swamp Shacks + Daimyo draw, Barbarian payload, Gold economy."
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule("Province", PriorityRule.resources("coins", ">=", 8)),
            PriorityRule(
                "Daimyo",
                PriorityRule.and_(
                    PriorityRule.resources("coins", ">=", 6),
                    PriorityRule.max_in_deck("Daimyo", 1),
                    PriorityRule.has_cards(["Swamp Shacks"], 2),
                ),
            ),
            PriorityRule("Gold", PriorityRule.max_in_deck("Gold", 2)),
            PriorityRule("Barbarian", PriorityRule.max_in_deck("Barbarian", 2)),
            PriorityRule("Quartermaster", PriorityRule.max_in_deck("Quartermaster", 1)),
            PriorityRule("Sculptor", PriorityRule.max_in_deck("Sculptor", 2)),
            PriorityRule(
                "Swamp Shacks",
                PriorityRule.and_(
                    PriorityRule.max_in_deck("Swamp Shacks", 3),
                    PriorityRule.has_cards(["Trail"], 2),
                ),
            ),
            PriorityRule("Trail", PriorityRule.max_in_deck("Trail", 6)),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 3)),
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
            _fountain_copper_rule(),
        ]
        self.action_priority = [
            PriorityRule("Trail"),
            PriorityRule("Quartermaster"),
            PriorityRule(
                "Daimyo",
                PriorityRule.or_(
                    PriorityRule.card_in_hand("Swamp Shacks"),
                    PriorityRule.card_in_hand("Barbarian"),
                ),
            ),
            PriorityRule("Swamp Shacks"),
            PriorityRule("Sculptor"),
            PriorityRule("Barbarian"),
            PriorityRule("Daimyo"),
        ]
        self.trash_priority = _junk_trash()
        self.treasure_priority = _money_treasures()


class PortMoresbyQuartermasterTrailEngine(EnhancedStrategy):
    """Two Quartermasters feed a Trail every turn; Swamp Shacks draws off them.

    A Trail gained by Quartermaster plays itself at the start of the turn
    (six-card hand) and both Quartermasters sit in play forever, so Swamp
    Shacks starts each turn with a head start on its cards-in-play count.
    """

    def __init__(self) -> None:
        super().__init__()
        self.name = "Port Moresby Quartermaster Trail Engine"
        self.description = "Quartermasters gain a Trail each turn; Swamp Shacks + Barbarian."
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule("Province", PriorityRule.resources("coins", ">=", 8)),
            PriorityRule("Quartermaster", PriorityRule.max_in_deck("Quartermaster", 2)),
            PriorityRule("Barbarian", PriorityRule.max_in_deck("Barbarian", 2)),
            PriorityRule("Gold", PriorityRule.max_in_deck("Gold", 2)),
            PriorityRule("Swamp Shacks", PriorityRule.max_in_deck("Swamp Shacks", 3)),
            PriorityRule("Trail", PriorityRule.max_in_deck("Trail", 8)),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 3)),
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
            _fountain_copper_rule(),
        ]
        self.action_priority = [
            PriorityRule("Trail"),
            PriorityRule("Quartermaster"),
            PriorityRule("Swamp Shacks"),
            PriorityRule("Barbarian"),
        ]
        self.trash_priority = _junk_trash()
        self.treasure_priority = _money_treasures()

    def choose_quartermaster_option(self, state, player, mat, candidates):
        # Always gain: a Trail plays itself immediately (+1 Card at turn
        # start) and never even reaches the mat. Fall back to Silver.
        for name in ("Trail", "Swamp Shacks", "Silver"):
            pick = next((c for c in candidates if c.name == name), None)
            if pick is not None:
                return "gain", pick
        if mat:
            return "take", max(mat, key=lambda c: (c.cost.coins, c.name))
        return "gain", (candidates[0] if candidates else None)


class PortMoresbyCopperMatMoney(EnhancedStrategy):
    """Hand-search leader before the island run: double Quartermaster money
    whose Quartermasters gain three Coppers onto the mat first (Fountain
    without drawing them), then bank Silvers taken only for a Province."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "Port Moresby Copper Mat Money"
        self.description = "Double Quartermaster money; Coppers to the mat first, then Silvers for Provinces."
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule("Province"),
            PriorityRule("Quartermaster", PriorityRule.max_in_deck("Quartermaster", 2)),
            PriorityRule("Gold"),
            PriorityRule("Barbarian", PriorityRule.max_in_deck("Barbarian", 1)),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 4)),
            PriorityRule("Silver"),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
            _fountain_copper_rule(),
        ]
        self.action_priority = [
            PriorityRule("Trail"),
            PriorityRule("Quartermaster"),
            PriorityRule("Barbarian"),
        ]
        self.trash_priority = _junk_trash()
        self.treasure_priority = _money_treasures()

    def choose_quartermaster_option(self, state, player, mat, candidates):
        def pick(cname):
            return next((c for c in candidates if c.name == cname), None)

        if player.count_in_deck("Copper") < 10 and pick("Copper") is not None:
            return "gain", pick("Copper")
        silvers = [c for c in mat if c.name == "Silver"]
        coins = sum(c.stats.coins for c in player.hand if c.is_treasure)
        provinces = state.supply.get("Province", 0)
        if silvers and coins < 8 and (coins + 2 * len(silvers) >= 8 or provinces <= 2):
            return "take", silvers[0]
        if pick("Silver") is not None:
            return "gain", pick("Silver")
        if mat:
            return "take", max(mat, key=lambda c: (c.cost.coins, c.name))
        return "gain", (candidates[0] if candidates else None)


def create_port_moresby_copper_mat_money() -> EnhancedStrategy:
    return PortMoresbyCopperMatMoney()


def create_port_moresby_barbarian_money() -> EnhancedStrategy:
    return PortMoresbyBarbarianMoney()


def create_port_moresby_quartermaster_money() -> EnhancedStrategy:
    return PortMoresbyQuartermasterMoney()


def create_port_moresby_double_quartermaster_money() -> EnhancedStrategy:
    return PortMoresbyDoubleQuartermasterMoney()


def create_port_moresby_sculptor_fountain_rush() -> EnhancedStrategy:
    return PortMoresbySculptorFountainRush()


def create_port_moresby_falconer_trail_engine() -> EnhancedStrategy:
    return PortMoresbyFalconerTrailEngine()


def create_port_moresby_swamp_daimyo_engine() -> EnhancedStrategy:
    return PortMoresbySwampDaimyoEngine()


def create_port_moresby_quartermaster_trail_engine() -> EnhancedStrategy:
    return PortMoresbyQuartermasterTrailEngine()

"""Island seeds for the Bilbao board (``boards/bilbao.txt``).

Kingdom: Fool's Gold (Rich), Grotto, Shaman, Anvil, Hermit, Sheepdog, Feodum,
Wandering Minstrel, Wheelwright, Raider. No Colony/Platinum, no Events.

Board texture
-------------
- There is no +Buy anywhere. Extra gains come only from Anvil (discard a
  Treasure, gain a card costing up to $4), Hermit (gain a card costing up
  to $3), Wheelwright (discard a card to gain an Action costing no more), the
  Rich trait (every Fool's Gold gained also gains a Silver) and Shaman's
  setup rule (each player's turn starts by gaining a card costing up to $6
  from the trash, mandatory).
- Rich Fool's Gold means a Fool's Gold deck fills with Silvers for free, and
  Feodum scores 1 VP per 3 Silvers. Anvil turns a Copper into "Fool's Gold +
  Silver" or a Feodum every time it is played.
- Shaman's setup rule makes trashing double-edged: a trashed Estate or
  Copper is handed to the next player, who must take it. Against a deck that
  cannot trash, Shaman is therefore a junking attack; in a mirror the junk
  ping-pongs. It also makes the Fool's Gold reaction free (the trashed
  Fool's Gold comes straight back at the start of the owner's next turn).
- Hermit exchanges itself for a Madman on a turn with no Buy-phase gain;
  Madman doubles the hand. Wandering Minstrel is the only village.
- Raider is a $6 Night card that pays +$3 next turn; played after Treasures,
  its attack makes five-card hands discard a copy of a card in play.

Each seed is a distinct theory of the kingdom for the island model.
"""

from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _hand_money(player) -> int:
    """Coins this hand can still produce (Fool's Gold bonus included)."""
    fg_played = getattr(player, "fools_gold_played", 0)
    total = player.coins
    for card in player.hand:
        if not card.is_treasure:
            continue
        if card.name == "Fool's Gold":
            total += 1 if fg_played == 0 else 4
            fg_played += 1
        else:
            total += card.stats.coins
    return total


def _money_treasures() -> list[PriorityRule]:
    """Play Anvil first so it can still discard a Copper for its gain."""
    return [
        PriorityRule("Anvil"),
        PriorityRule("Gold"),
        PriorityRule("Fool's Gold"),
        PriorityRule("Silver"),
        PriorityRule("Copper"),
    ]


def _anvil_discard_value(player, card) -> int:
    """Coins the hand loses by discarding ``card`` to Anvil."""
    if card.name == "Fool's Gold":
        first = getattr(player, "fools_gold_played", 0) == 0 and not any(
            c.name == "Fool's Gold" for c in player.in_play
        )
        only_one = sum(1 for c in player.hand if c.name == "Fool's Gold") == 1
        return 1 if first and only_one else 4
    return card.stats.coins


def _anvil_gain_guard(state, player, choices, base, discard_pick=None):
    """Skip the Anvil gain when the discard it needs would cost a Province.

    ``discard_pick`` is the Treasure that will actually be discarded (the
    fallback can be a Silver, not just a Copper); without it, assume $1.
    """
    treasures = [c for c in player.hand if c.is_treasure]
    discard = discard_pick(player, treasures) if discard_pick else None
    if discard_pick and discard is None:
        return None
    lost = _anvil_discard_value(player, discard) if discard is not None else 1
    money = _hand_money(player)
    if money >= 8 and money - lost < 8:
        return None
    return base(state, player, choices)


def _anvil_discard(player, choices):
    """Copper first; a lone first Fool's Gold ($1) next; then a Silver."""
    for card in choices:
        if card.name == "Copper":
            return card
    fg_in_hand = [c for c in choices if c.name == "Fool's Gold"]
    if (
        len(fg_in_hand) == 1
        and getattr(player, "fools_gold_played", 0) == 0
        and not any(c.name == "Fool's Gold" for c in player.in_play)
    ):
        return fg_in_hand[0]
    for card in choices:
        if card.name == "Silver":
            return card
    return None


class _BilbaoBase(EnhancedStrategy):
    """Shared Anvil policy and the always-on Fool's Gold reaction."""

    def choose_anvil_gain(self, state, player, choices):
        return _anvil_gain_guard(
            state, player, choices, super().choose_gain, _anvil_discard
        )

    def choose_anvil_treasure_to_discard(self, state, player, choices):
        return _anvil_discard(player, choices)

    # The Fool's Gold reaction follows the AI default: with Shaman's setup
    # rule it fires once per trigger when this player acts next.


# ---------------------------------------------------------------------------
# Seeds
# ---------------------------------------------------------------------------


class BilbaoFoolsGoldRush(_BilbaoBase):
    """Fool's Gold money: every Fool's Gold also brings a Silver (Rich), two
    Anvils turn Coppers into more Fool's Golds, Feodums cash in the Silvers
    late."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "Bilbao Fools Gold Rush"
        self.description = "Rich Fool's Gold money with two Anvils and late Feodums."
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule("Province", PriorityRule.resources("coins", ">=", 8)),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 4)),
            PriorityRule("Gold", PriorityRule.resources("coins", ">=", 6)),
            PriorityRule(
                "Anvil",
                PriorityRule.and_(
                    PriorityRule.max_in_deck("Anvil", 2),
                    PriorityRule.turn_number("<=", 8),
                ),
            ),
            PriorityRule("Feodum", PriorityRule.provinces_left("<=", 3)),
            PriorityRule("Fool's Gold", PriorityRule.max_in_deck("Fool's Gold", 10)),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
            PriorityRule("Silver"),
        ]
        self.treasure_priority = _money_treasures()


class BilbaoAnvilFeodumSlog(_BilbaoBase):
    """Feodum slog: three Anvils gain Fool's Golds (each with a Silver) and
    then Feodums; the Silvers make every Feodum worth 3-4 VP."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "Bilbao Anvil Feodum Slog"
        self.description = "Anvils gain Fool's Gold+Silver early, Feodums once Silvers pile up."
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule("Province", PriorityRule.resources("coins", ">=", 8)),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 5)),
            PriorityRule(
                "Anvil",
                PriorityRule.and_(
                    PriorityRule.max_in_deck("Anvil", 3),
                    PriorityRule.turn_number("<=", 10),
                ),
            ),
            PriorityRule("Feodum", PriorityRule.has_cards(["Silver"], 6)),
            PriorityRule("Gold", PriorityRule.resources("coins", ">=", 6)),
            PriorityRule("Fool's Gold", PriorityRule.max_in_deck("Fool's Gold", 8)),
            PriorityRule("Feodum", PriorityRule.provinces_left("<=", 4)),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
            PriorityRule("Silver"),
        ]
        self.treasure_priority = _money_treasures()


class BilbaoRaiderMoney(_BilbaoBase):
    """Big Money with two Raiders (a Gold that pays next turn and nudges the
    opponent) and one early Anvil."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "Bilbao Raider Money"
        self.description = "Big Money with two Raiders and one Anvil."
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule("Province", PriorityRule.resources("coins", ">=", 8)),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 4)),
            PriorityRule(
                "Raider",
                PriorityRule.and_(
                    PriorityRule.max_in_deck("Raider", 2),
                    PriorityRule.turn_number("<=", 12),
                ),
            ),
            PriorityRule("Gold"),
            PriorityRule(
                "Anvil",
                PriorityRule.and_(
                    PriorityRule.max_in_deck("Anvil", 1),
                    PriorityRule.turn_number("<=", 6),
                ),
            ),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
            PriorityRule("Silver"),
        ]
        self.action_priority = [PriorityRule("Raider")]
        self.treasure_priority = _money_treasures()


class BilbaoHermitMadmanEngine(_BilbaoBase):
    """Hermit/Madman draw engine: Hermits gain Sheepdogs and Fool's Golds,
    a Hermit turn with no Buy-phase gain becomes a Madman, Wandering
    Minstrels supply Actions, Fool's Golds are the payload."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "Bilbao Hermit Madman Engine"
        self.description = "Hermits gain Sheepdogs/Fool's Golds, become Madmen; Minstrel villages."
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule("Province", PriorityRule.resources("coins", ">=", 8)),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 3)),
            PriorityRule("Gold", PriorityRule.resources("coins", ">=", 6)),
            PriorityRule(
                "Wandering Minstrel",
                PriorityRule.and_(
                    PriorityRule.max_in_deck("Wandering Minstrel", 3),
                    PriorityRule.has_cards(["Hermit", "Sheepdog"], 2),
                ),
            ),
            PriorityRule("Hermit", PriorityRule.max_in_deck("Hermit", 3)),
            PriorityRule("Sheepdog", PriorityRule.max_in_deck("Sheepdog", 4)),
            PriorityRule("Fool's Gold", PriorityRule.max_in_deck("Fool's Gold", 6)),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
            PriorityRule("Silver"),
        ]
        self.action_priority = [
            PriorityRule("Wandering Minstrel"),
            PriorityRule("Madman"),
            PriorityRule("Shaman"),
            PriorityRule("Wheelwright"),
            PriorityRule("Hermit"),
            PriorityRule("Sheepdog"),
            PriorityRule("Raider"),
        ]
        self.trash_priority = [PriorityRule("Curse"), PriorityRule("Estate")]
        self.treasure_priority = _money_treasures()

    def choose_gain(self, state, player, choices):
        # Madman conversion: on a weak Buy phase with a Hermit in play, buy
        # nothing so the Hermit exchanges itself for a Madman.
        if (
            getattr(state, "phase", None) == "buy"
            and any(c.name == "Hermit" for c in player.in_play)
            and player.coins <= 4
            and state.supply.get("Madman", 0) > 0
        ):
            return None
        return super().choose_gain(state, player, choices)


class BilbaoShamanPeddler(_BilbaoBase):
    """Shaman peddler deck: many cantrip +$1 Shamans thin Coppers and
    Estates (which the opponent must then take from the trash), Wheelwright
    cantrips, Golds and a Raider for payload."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "Bilbao Shaman Peddler"
        self.description = "Shaman cantrips trash junk onto the opponent; Gold/Raider payload."
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule("Province", PriorityRule.resources("coins", ">=", 8)),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 3)),
            PriorityRule("Gold", PriorityRule.resources("coins", ">=", 6)),
            PriorityRule(
                "Raider",
                PriorityRule.and_(
                    PriorityRule.max_in_deck("Raider", 1),
                    PriorityRule.resources("coins", ">=", 6),
                ),
            ),
            PriorityRule("Wheelwright", PriorityRule.max_in_deck("Wheelwright", 2)),
            PriorityRule("Shaman", PriorityRule.max_in_deck("Shaman", 6)),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
            PriorityRule("Silver"),
            PriorityRule("Shaman"),
        ]
        self.action_priority = [
            PriorityRule("Wandering Minstrel"),
            PriorityRule("Shaman"),
            PriorityRule("Wheelwright"),
            PriorityRule("Grotto"),
            PriorityRule("Raider"),
        ]
        self.trash_priority = [
            PriorityRule("Curse"),
            PriorityRule("Estate"),
            PriorityRule("Copper", PriorityRule.turn_number("<=", 12)),
        ]
        self.treasure_priority = _money_treasures()


class BilbaoSheepdogAnvilMoney(_BilbaoBase):
    """Anvil money where Sheepdogs react to every Anvil gain and every Rich
    Silver, drawing two cards mid-Buy phase."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "Bilbao Sheepdog Anvil Money"
        self.description = "Anvils gain Fool's Golds; Sheepdogs react to the gains for draw."
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule("Province", PriorityRule.resources("coins", ">=", 8)),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 4)),
            PriorityRule("Gold", PriorityRule.resources("coins", ">=", 6)),
            PriorityRule(
                "Anvil",
                PriorityRule.and_(
                    PriorityRule.max_in_deck("Anvil", 3),
                    PriorityRule.turn_number("<=", 10),
                ),
            ),
            PriorityRule(
                "Sheepdog",
                PriorityRule.and_(
                    PriorityRule.max_in_deck("Sheepdog", 3),
                    PriorityRule.has_cards(["Anvil"], 1),
                ),
            ),
            PriorityRule("Feodum", PriorityRule.provinces_left("<=", 3)),
            PriorityRule("Fool's Gold", PriorityRule.max_in_deck("Fool's Gold", 8)),
            PriorityRule("Estate", PriorityRule.provinces_left("<=", 2)),
            PriorityRule("Silver"),
        ]
        # Keep Sheepdogs in hand for the reaction when an Anvil is in hand.
        self.action_priority = [
            PriorityRule(
                "Sheepdog",
                PriorityRule.has_no_cards(["Anvil"]),
            ),
        ]
        self.treasure_priority = _money_treasures()

    def choose_action(self, state, player, choices):
        anvil_in_hand = any(c.name == "Anvil" for c in player.hand)
        if not anvil_in_hand:
            sheepdog = next((c for c in choices if c is not None and c.name == "Sheepdog"), None)
            if sheepdog is not None:
                return sheepdog
        return super().choose_action(state, player, choices)


# ---------------------------------------------------------------------------
# Loader factories
# ---------------------------------------------------------------------------


def create_bilbao_fools_gold_rush() -> EnhancedStrategy:
    return BilbaoFoolsGoldRush()


def create_bilbao_anvil_feodum_slog() -> EnhancedStrategy:
    return BilbaoAnvilFeodumSlog()


def create_bilbao_raider_money() -> EnhancedStrategy:
    return BilbaoRaiderMoney()


def create_bilbao_hermit_madman_engine() -> EnhancedStrategy:
    return BilbaoHermitMadmanEngine()


def create_bilbao_shaman_peddler() -> EnhancedStrategy:
    return BilbaoShamanPeddler()


def create_bilbao_sheepdog_anvil_money() -> EnhancedStrategy:
    return BilbaoSheepdogAnvilMoney()


# ---------------------------------------------------------------------------
# Parametrised leader for hand local search (not loader-registered)
# ---------------------------------------------------------------------------


class BilbaoAnvilFeodumVariant(_BilbaoBase):
    """Anvil/Feodum money with every structural knob exposed.

    Used by ``scripts/bilbao_variants.py`` to sweep the neighbourhood of the
    round-robin leader; the GA cannot move the Anvil hooks, and the sweep
    tells us which knobs matter before evolution starts.
    """

    def __init__(
        self,
        name: str = "Bilbao Anvil Feodum Variant",
        anvils: int = 3,
        anvil_turn: int = 10,
        feodum_silvers: int = 6,
        feodum_max: int = 8,
        feodum_late: int = 4,
        duchy_gate: int = 5,
        gold_min: int = 6,
        gold_max: int = 99,
        fg_max: int = 8,
        estate_gate: int = 2,
        province_min: int = 8,
        raiders: int = 0,
        wheelwrights: int = 0,
        sheepdogs: int = 0,
        feodum_before_gold: bool = True,
        fg_before_silver: bool = True,
        hermits: int = 0,
        anvil_gain: str = "list",
        anvil_discard_silver: bool = True,
        feodum_over_province_silvers: int = 99,
        feodum_over_duchy_silvers: int = 99,
        shamans: int = 0,
        shaman_trash: str = "copper_estate",
        grottos: int = 0,
    ) -> None:
        super().__init__()
        self.name = name
        self.description = "Parametrised Anvil/Feodum money for hand search."
        self.version = "1.0"
        self.params = dict(
            anvils=anvils, anvil_turn=anvil_turn, feodum_silvers=feodum_silvers,
            feodum_max=feodum_max, feodum_late=feodum_late, duchy_gate=duchy_gate,
            gold_min=gold_min, gold_max=gold_max, fg_max=fg_max, estate_gate=estate_gate,
            province_min=province_min, raiders=raiders, wheelwrights=wheelwrights,
            sheepdogs=sheepdogs, feodum_before_gold=feodum_before_gold,
            fg_before_silver=fg_before_silver, hermits=hermits,
            anvil_gain=anvil_gain, anvil_discard_silver=anvil_discard_silver,
            feodum_over_province_silvers=feodum_over_province_silvers,
            feodum_over_duchy_silvers=feodum_over_duchy_silvers,
            shamans=shamans, shaman_trash=shaman_trash, grottos=grottos,
        )

        feodum_rule = PriorityRule(
            "Feodum",
            PriorityRule.and_(
                PriorityRule.has_cards(["Silver"], feodum_silvers),
                PriorityRule.max_in_deck("Feodum", feodum_max),
            ),
        )
        gold_rule = PriorityRule(
            "Gold",
            PriorityRule.and_(
                PriorityRule.resources("coins", ">=", gold_min),
                PriorityRule.max_in_deck("Gold", gold_max),
            ),
        )
        def feodum_when_silvers(n: int) -> PriorityRule:
            return PriorityRule(
                "Feodum",
                PriorityRule.and_(
                    PriorityRule.has_cards(["Silver"], n),
                    PriorityRule.max_in_deck("Feodum", feodum_max),
                ),
            )

        rules = [
            feodum_when_silvers(feodum_over_province_silvers),
            PriorityRule("Province", PriorityRule.resources("coins", ">=", province_min)),
            feodum_when_silvers(feodum_over_duchy_silvers),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", duchy_gate)),
        ]
        if raiders:
            rules.append(
                PriorityRule(
                    "Raider",
                    PriorityRule.and_(
                        PriorityRule.max_in_deck("Raider", raiders),
                        PriorityRule.turn_number("<=", 12),
                    ),
                )
            )
        rules.append(
            PriorityRule(
                "Anvil",
                PriorityRule.and_(
                    PriorityRule.max_in_deck("Anvil", anvils),
                    PriorityRule.turn_number("<=", anvil_turn),
                ),
            )
        )
        if wheelwrights:
            rules.append(
                PriorityRule("Wheelwright", PriorityRule.max_in_deck("Wheelwright", wheelwrights))
            )
        if shamans:
            rules.append(
                PriorityRule(
                    "Shaman",
                    PriorityRule.and_(
                        PriorityRule.max_in_deck("Shaman", shamans),
                        PriorityRule.turn_number("<=", 10),
                    ),
                )
            )
        if grottos:
            rules.append(
                PriorityRule(
                    "Grotto",
                    PriorityRule.and_(
                        PriorityRule.max_in_deck("Grotto", grottos),
                        PriorityRule.turn_number("<=", 10),
                    ),
                )
            )
        if hermits:
            rules.append(
                PriorityRule(
                    "Hermit",
                    PriorityRule.and_(
                        PriorityRule.max_in_deck("Hermit", hermits),
                        PriorityRule.turn_number("<=", 8),
                    ),
                )
            )
        if sheepdogs:
            rules.append(
                PriorityRule(
                    "Sheepdog",
                    PriorityRule.and_(
                        PriorityRule.max_in_deck("Sheepdog", sheepdogs),
                        PriorityRule.has_cards(["Anvil"], 1),
                    ),
                )
            )
        rules += [feodum_rule, gold_rule] if feodum_before_gold else [gold_rule, feodum_rule]
        fg_rule = PriorityRule("Fool's Gold", PriorityRule.max_in_deck("Fool's Gold", fg_max))
        late_feodum = PriorityRule("Feodum", PriorityRule.provinces_left("<=", feodum_late))
        estate_rule = PriorityRule("Estate", PriorityRule.provinces_left("<=", estate_gate))
        if fg_before_silver:
            rules += [fg_rule, late_feodum, estate_rule, PriorityRule("Silver")]
        else:
            rules += [late_feodum, estate_rule, PriorityRule("Silver"), fg_rule]
        self.gain_priority = rules
        self.action_priority = [
            PriorityRule("Wandering Minstrel"),
            PriorityRule("Shaman"),
            PriorityRule("Grotto"),
            PriorityRule("Wheelwright"),
            PriorityRule("Hermit"),
            PriorityRule("Sheepdog"),
            PriorityRule("Raider"),
        ]
        self.trash_priority = [PriorityRule("Curse")]
        if shaman_trash in ("copper_estate", "estate"):
            self.trash_priority.append(PriorityRule("Estate"))
        if shaman_trash == "copper_estate":
            self.trash_priority.append(PriorityRule("Copper"))
        self.treasure_priority = _money_treasures()

    def _choose_anvil_gain(self, state, player, choices):
        mode = self.params["anvil_gain"]
        if mode == "fg":
            fg = next((c for c in choices if c.name == "Fool's Gold"), None)
            if fg is not None and player.count_in_deck("Fool's Gold") < self.params["fg_max"]:
                return _anvil_gain_guard(
                    state, player, choices, lambda *_: fg, self._variant_discard
                )
        elif mode == "feodum":
            feodum = next((c for c in choices if c.name == "Feodum"), None)
            if feodum is not None:
                return _anvil_gain_guard(
                    state, player, choices, lambda *_: feodum, self._variant_discard
                )
        return _anvil_gain_guard(
            state, player, choices, super().choose_gain, self._variant_discard
        )

    def _variant_discard(self, player, choices):
        pick = _anvil_discard(player, choices)
        if pick is not None and pick.name == "Silver" and not self.params["anvil_discard_silver"]:
            return None
        return pick

    def choose_anvil_gain(self, state, player, choices):  # noqa: F811
        return self._choose_anvil_gain(state, player, choices)

    def choose_anvil_treasure_to_discard(self, state, player, choices):
        return self._variant_discard(player, choices)


# ---------------------------------------------------------------------------
# Shaman / Feodum Silver mill (parametrised; two configurations registered)
# ---------------------------------------------------------------------------


class BilbaoShamanFeodumMill(_BilbaoBase):
    """Trash Feodums for Silvers: Shamans and Hermits turn every $4 Feodum
    into three Silvers (Hermit adds a fourth), the Silvers make the Feodums
    kept at the end worth 4-8 VP each.

    Shaman's setup rule hands each trashed Feodum to the opponent at the
    start of their turn, so the mill also feeds them; when two Feodums are
    trashed in one turn the second one comes back to this player instead.
    Knobs cover how many Shamans/Hermits/Anvils to buy, when to stop
    trashing, and when Feodums outscore Provinces.
    """

    def __init__(
        self,
        name: str = "Bilbao Shaman Feodum Mill",
        shamans: int = 2,
        shaman_turn: int = 8,
        shaman_min_coins: int = 2,
        shaman_max_coins: int = 3,
        hermits: int = 1,
        hermit_turn: int = 8,
        anvils: int = 0,
        anvil_turn: int = 10,
        anvil_gain: str = "list",
        fodder_max: int = 2,
        fodder_turn: int = 99,
        fodder_min_coins: int = 4,
        feodum_silvers: int = 9,
        feodum_max: int = 8,
        feodum_over_province_silvers: int = 99,
        feodum_over_duchy_silvers: int = 99,
        feodum_late: int = 4,
        trash_stop_provinces: int = 2,
        trash_stop_pile: int = 0,
        trash_turn_max: int = 99,
        trash_mode: str = "always",
        trash_silver_cap: int = 99,
        trash_estates: bool = False,
        trash_coppers: bool = False,
        trash_keep_feodums: int = 0,
        gold_min: int = 6,
        fg_max: int = 0,
        fg_before_silver: bool = True,
        duchy_gate: int = 5,
        province_min: int = 8,
        hermit_gain: str = "silver",
        madman: bool = False,
        avoid_madman: bool = True,
    ) -> None:
        super().__init__()
        self.name = name
        self.description = "Shamans and Hermits trash Feodums for Silvers."
        self.version = "1.0"
        self.params = dict(
            shamans=shamans, shaman_turn=shaman_turn, shaman_min_coins=shaman_min_coins,
            shaman_max_coins=shaman_max_coins,
            hermits=hermits, hermit_turn=hermit_turn, anvils=anvils, anvil_turn=anvil_turn,
            anvil_gain=anvil_gain, fodder_max=fodder_max, fodder_turn=fodder_turn,
            fodder_min_coins=fodder_min_coins, feodum_silvers=feodum_silvers,
            feodum_max=feodum_max,
            feodum_over_province_silvers=feodum_over_province_silvers,
            feodum_over_duchy_silvers=feodum_over_duchy_silvers, feodum_late=feodum_late,
            trash_stop_provinces=trash_stop_provinces, trash_stop_pile=trash_stop_pile,
            trash_turn_max=trash_turn_max, trash_mode=trash_mode,
            trash_silver_cap=trash_silver_cap,
            trash_estates=trash_estates, trash_coppers=trash_coppers,
            trash_keep_feodums=trash_keep_feodums, gold_min=gold_min, fg_max=fg_max,
            fg_before_silver=fg_before_silver, duchy_gate=duchy_gate,
            province_min=province_min, hermit_gain=hermit_gain, madman=madman,
            avoid_madman=avoid_madman,
        )

        def feodum_when_silvers(n: int) -> PriorityRule:
            return PriorityRule(
                "Feodum",
                PriorityRule.and_(
                    PriorityRule.has_cards(["Silver"], n),
                    PriorityRule.max_in_deck("Feodum", feodum_max),
                ),
            )

        has_trasher = PriorityRule.or_(
            PriorityRule.has_cards(["Shaman"], 1), PriorityRule.has_cards(["Hermit"], 1)
        )
        rules = [
            feodum_when_silvers(feodum_over_province_silvers),
            PriorityRule("Province", PriorityRule.resources("coins", ">=", province_min)),
            feodum_when_silvers(feodum_over_duchy_silvers),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", duchy_gate)),
        ]
        if anvils:
            rules.append(
                PriorityRule(
                    "Anvil",
                    PriorityRule.and_(
                        PriorityRule.max_in_deck("Anvil", anvils),
                        PriorityRule.turn_number("<=", anvil_turn),
                    ),
                )
            )
        if shamans:
            rules.append(
                PriorityRule(
                    "Shaman",
                    PriorityRule.and_(
                        PriorityRule.max_in_deck("Shaman", shamans),
                        PriorityRule.turn_number("<=", shaman_turn),
                        PriorityRule.resources("coins", ">=", shaman_min_coins),
                        PriorityRule.resources("coins", "<=", shaman_max_coins),
                    ),
                )
            )
        if hermits:
            rules.append(
                PriorityRule(
                    "Hermit",
                    PriorityRule.and_(
                        PriorityRule.max_in_deck("Hermit", hermits),
                        PriorityRule.turn_number("<=", hermit_turn),
                    ),
                )
            )
        # The trash policy's cutoffs, built once as a tagged condition so the
        # catalog can render them and so ``_mill_active`` (used by the trash
        # and Anvil decisions below) and the fodder rule share one source of
        # truth: Silver pile, Province stop, Feodum-pile stop, turn max and
        # Silver cap.
        self._mill_gate = PriorityRule.and_(
            PriorityRule.pile_count("Silver", ">=", 3),
            PriorityRule.provinces_left(">", trash_stop_provinces),
            PriorityRule.pile_count("Feodum", ">", trash_stop_pile),
            PriorityRule.turn_number("<=", trash_turn_max),
            PriorityRule.max_in_deck("Silver", trash_silver_cap),
        )
        # Fodder: a Feodum bought to be trashed. Only while a trasher exists,
        # only while the trash policy is still active, and never more than
        # ``fodder_max`` in the deck at once.
        rules.append(
            PriorityRule(
                "Feodum",
                PriorityRule.and_(
                    has_trasher,
                    self._mill_gate,
                    PriorityRule.max_in_deck("Feodum", fodder_max),
                    PriorityRule.turn_number("<=", fodder_turn),
                    PriorityRule.resources("coins", ">=", fodder_min_coins),
                ),
            )
        )
        rules.append(feodum_when_silvers(feodum_silvers))
        # Gold after Anvil and the Feodum-from-Silvers rule, mirroring
        # ``BilbaoBestFound`` so the chassis variants are an exact control.
        rules.append(PriorityRule("Gold", PriorityRule.resources("coins", ">=", gold_min)))
        fg_rule = PriorityRule("Fool's Gold", PriorityRule.max_in_deck("Fool's Gold", fg_max))
        late_feodum = PriorityRule("Feodum", PriorityRule.provinces_left("<=", feodum_late))
        if fg_max and fg_before_silver:
            rules += [fg_rule, late_feodum, PriorityRule("Silver")]
        elif fg_max:
            rules += [late_feodum, PriorityRule("Silver"), fg_rule]
        else:
            rules += [late_feodum, PriorityRule("Silver")]
        self.gain_priority = rules

        self.action_priority = [
            PriorityRule("Shaman"),
            PriorityRule("Wandering Minstrel"),
            PriorityRule("Madman"),
            PriorityRule("Hermit"),
        ]
        self.treasure_priority = _money_treasures()
        self.trash_priority = []  # choose_trash is hand-written below

    # ---- trash policy ----------------------------------------------------

    def _mill_active(self, state, player) -> bool:
        return bool(self._mill_gate(state, player))

    def _pair_available(self, state, player, via_hermit: bool) -> bool:
        """Can a second Feodum go to the trash this turn, so that the
        opponent takes one and this player gets the other back?"""
        if any(c.name == "Feodum" for c in state.trash):
            return True
        if via_hermit:
            return False  # Hermit is terminal: nothing plays after it
        # The second trash still has to pass ``_mill_active`` after this
        # trash's Silvers land (three now, plus Hermit's own gain), so a
        # near-empty Silver pile or a player close to ``trash_silver_cap``
        # cannot promise a pair. Four is a conservative bound for both.
        if state.supply.get("Silver", 0) - 4 < 3:
            return False
        if player.count_in_deck("Silver") + 4 >= self.params["trash_silver_cap"]:
            return False
        # ...and the second trash must still leave ``trash_keep_feodums``.
        if player.count_in_deck("Feodum") - 1 <= self.params["trash_keep_feodums"]:
            return False
        hand_feodums = sum(1 for c in player.hand if c.name == "Feodum") - 1
        discard_feodums = sum(1 for c in player.discard if c.name == "Feodum")
        shamans = sum(1 for c in player.hand if c.name == "Shaman")
        hermits = sum(1 for c in player.hand if c.name == "Hermit")
        if shamans and hand_feodums >= 1:
            return True
        if hermits and (hand_feodums >= 1 or discard_feodums >= 1):
            return True
        return False

    def _pick_trash(self, state, player, choices, via_hermit: bool = False):
        p = self.params
        feodums = [c for c in choices if c is not None and c.name == "Feodum"]
        if feodums and self._mill_active(state, player):
            keep_ok = player.count_in_deck("Feodum") > p["trash_keep_feodums"]
            mode_ok = p["trash_mode"] == "always" or (
                p["trash_mode"] == "pair" and self._pair_available(state, player, via_hermit)
            )
            if keep_ok and mode_ok:
                return feodums[0]
        if p["trash_estates"]:
            estate = next((c for c in choices if c is not None and c.name == "Estate"), None)
            if estate is not None:
                return estate
        if p["trash_coppers"] and state.turn_number <= 12:
            copper = next((c for c in choices if c is not None and c.name == "Copper"), None)
            if copper is not None:
                return copper
        return None

    def choose_trash(self, state, player, choices):
        return self._pick_trash(state, player, choices)

    def should_trash_with_hermit(self, state, player, choices):
        return self._pick_trash(state, player, choices, via_hermit=True)

    def choose_hermit_gain(self, state, player, choices):
        p = self.params
        names = {c.name: c for c in choices}
        if "Shaman" in names and player.count_in_deck("Shaman") < p["shamans"]:
            return names["Shaman"]
        if p["hermit_gain"] == "silver" and "Silver" in names:
            return names["Silver"]
        return None

    def choose_shaman_gain(self, state, player, choices):
        """Start-of-turn gain from the trash: take a Feodum back first."""
        feodum = next((c for c in choices if c.name == "Feodum"), None)
        if feodum is not None:
            return feodum
        return None

    # ---- Anvil ------------------------------------------------------------

    def choose_anvil_gain(self, state, player, choices):
        if self.params["anvil_gain"] == "feodum":
            feodum = next((c for c in choices if c.name == "Feodum"), None)
            if (
                feodum is not None
                and self._mill_active(state, player)
                and player.count_in_deck("Feodum") < self.params["fodder_max"]
            ):
                return _anvil_gain_guard(
                    state, player, choices, lambda *_: feodum, _anvil_discard
                )
        return _anvil_gain_guard(
            state, player, choices, super().choose_gain, _anvil_discard
        )

    # ---- Madman -----------------------------------------------------------

    def choose_gain(self, state, player, choices):
        if (
            self.params["madman"]
            and getattr(state, "phase", None) == "buy"
            and any(c.name == "Hermit" for c in player.in_play)
            and player.coins <= 3
            and state.supply.get("Madman", 0) > 0
        ):
            return None
        pick = super().choose_gain(state, player, choices)
        if (
            pick is None
            and self.params["avoid_madman"]
            and getattr(state, "phase", None) == "buy"
            and any(c.name == "Hermit" for c in player.in_play)
        ):
            pick = next((c for c in choices if c is not None and c.name == "Copper"), None)
        return pick


def create_bilbao_shaman_feodum_mill() -> EnhancedStrategy:
    """Two Shamans and two Hermits trash Feodums for Silvers (the user's
    mill idea in its best pure form). Loses every game to Bilbao Best Found;
    see ``reports/strategies/bilbao-shaman-feodum-mill-strategy-guide.html``."""
    return BilbaoShamanFeodumMill(name="Bilbao Shaman Feodum Mill", hermits=2)


def create_bilbao_shaman_feodum_mill_hybrid() -> EnhancedStrategy:
    """Best Found chassis plus two Shamans and a Hermit that trash Feodums
    only in pairs (so one comes back). The strongest mill variant found:
    81% against the seed field, 13% against Bilbao Best Found."""
    return BilbaoShamanFeodumMill(
        name="Bilbao Shaman Feodum Mill Hybrid",
        trash_mode="pair",
        shamans=2,
        hermits=1,
        anvils=3,
        fg_max=8,
        feodum_silvers=3,
        duchy_gate=6,
        gold_min=7,
        fodder_max=0,
    )

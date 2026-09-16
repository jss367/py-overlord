"""Tunable policies for the ten-unused-card Groundskeeper / Margrave board.

Board
-----
Cellar, Oasis, Fishing Village, Moneylender, Monument, Junk Dealer, Library,
Margrave, Groundskeeper, Border Village. Every pile was unreferenced by any
registered strategy when the board was drawn.

The board's real question is which payload wins. Monument turns a terminal
slot into +$2 and a VP token, which suits a money deck. Groundskeeper scores a
VP token for *every* victory card gained while it is in play, which rewards an
engine that greens early and buys several green cards a turn. ``search_
groundskeeper_margrave.py`` plays the knobs below against each other; the
factories at the bottom are the policies that survived that search.
"""

from collections import Counter

from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


#: Cards this family never wants to feed to Junk Dealer or Cellar.
_ENGINE_PIECES = frozenset(
    {
        "Fishing Village",
        "Border Village",
        "Margrave",
        "Library",
        "Groundskeeper",
        "Junk Dealer",
        "Monument",
        "Oasis",
        "Gold",
    }
)


#: Discard requests that are both mandatory *and* whose callers accept a short
#: answer as the player's whole choice. For these -- and only these -- the hook
#: below tops its junk-first selection up to ``count``.
#:
#: Every other mandatory discard in the engine fills the gap itself, either with
#: an explicit fallback (Militia, Goons, Legionary, Samurai, Ninja, Footpad,
#: Sword, Poacher, Warehouse, Sea Witch, Tide Pools, Forum, Dungeon, Young
#: Witch, Horse Traders, Soldier, Villain, Ferryman, Count, Catapult, Diplomat,
#: Scouting Party, Sycophant, Sibyl and ``allies/_rules.discard``) or with a
#: ``while len(hand) > n`` loop that keeps asking (Mercenary, Urchin, Sir
#: Michael). Filling those too would be harmless but pointless; filling the
#: *optional* effects would be actively wrong, which is why this is an explicit
#: list and not "everything except Cellar".
#:
#: Because this list is keyed on ``reason``, a mandatory caller that passed no
#: reason could never appear in it. Every discard request in ``dominion/`` now
#: names itself -- the last six anonymous ones were the Boons and Hexes, split
#: as The Sky's Gift and The Sun's Gift (optional, so deliberately absent
#: below), Fear, Haunting and Poverty (mandatory but self-filling, like
#: Militia) and The Wind's Gift (mandatory with no fallback, so listed).
#: ``test_every_engine_discard_request_names_its_caller`` keeps it that way.
_MANDATORY_DISCARDS = frozenset(
    {
        # Torturer: takes any nonempty result as the choice, so a short answer
        # discards one card instead of two and the attack is under-paid.
        "torturer",
        # Fugitive: returns without discarding at all if the result is empty.
        "fugitive",
        # Alley: same shape as Fugitive -- discard a card, no fallback.
        "alley",
        # Marquis: discard down to ten, sliced to ``picks[:excess]``.
        "marquis",
        # Sickness (Prophecy): the Curse-or-discard choice is already made, and
        # the discard branch slices to ``chosen[:count]``.
        "sickness",
        # The Wind's Gift: "+2 Cards. Discard 2 cards." The Boon slices to
        # ``discards[:count]`` and has no fallback, so a hand with fewer than
        # two junk cards would under-pay a discard that is not optional.
        "the_winds_gift",
    }
)


class GroundskeeperMargrave(EnhancedStrategy):
    """One parameterized deck plan for the Groundskeeper / Margrave board.

    Every knob is a deck cap except ``green``/``duchy``/``estate_vp``, which
    control when the deck turns the corner, and ``opening``, which fixes the
    first two buys.
    """

    def __init__(
        self,
        *,
        groundskeeper=0,
        margrave=0,
        library=0,
        monument=0,
        moneylender=0,
        junk_dealer=0,
        fishing_village=0,
        border_village=0,
        oasis=0,
        cellar=0,
        silvers=2,
        golds=99,
        green=10,
        duchy=4,
        estate_vp=False,
        opening="Silver",
    ):
        super().__init__()
        self.name = "Groundskeeper Margrave"
        self.description = (
            "Tunable Groundskeeper / Margrave board policy: villages and draw "
            "supporting either Monument tokens or Groundskeeper greening."
        )
        self.params = dict(
            groundskeeper=groundskeeper,
            margrave=margrave,
            library=library,
            monument=monument,
            moneylender=moneylender,
            junk_dealer=junk_dealer,
            fishing_village=fishing_village,
            border_village=border_village,
            oasis=oasis,
            cellar=cellar,
            silvers=silvers,
            golds=golds,
            green=green,
            duchy=duchy,
            estate_vp=estate_vp,
            opening=opening,
        )

        # Villages first so terminals never strand; Groundskeeper before the
        # draw terminals so its bonus is live for anything gained this turn.
        self.action_priority = [
            PriorityRule(name)
            for name in (
                "Fishing Village",
                "Border Village",
                "Groundskeeper",
                "Oasis",
                "Junk Dealer",
                "Cellar",
                "Margrave",
                "Library",
                "Monument",
                "Moneylender",
            )
        ]
        self.treasure_priority = [
            PriorityRule(name) for name in ("Gold", "Silver", "Copper")
        ]
        self.gain_priority = [
            PriorityRule(name)
            for name in (
                "Province",
                "Duchy",
                "Estate",
                "Gold",
                "Silver",
                "Border Village",
                "Margrave",
                "Groundskeeper",
                "Library",
                "Junk Dealer",
                "Monument",
                "Moneylender",
                "Fishing Village",
                "Oasis",
                "Cellar",
            )
        ]

    # -- helpers -------------------------------------------------------
    @staticmethod
    def pick(choices, names):
        available = {c.name: c for c in choices if c is not None}
        return next((available[n] for n in names if n in available), None)

    def _terminals(self):
        p = self.params
        return p["margrave"] + p["library"] + p["monument"] + p["moneylender"]

    # -- play order ----------------------------------------------------
    def choose_action(self, state, player, choices):
        available = {c.name for c in choices if c is not None}
        names = ["Fishing Village", "Border Village"]

        # Groundskeeper only pays when a victory card is still gained this
        # turn, which needs either buying power in hand or a spare buy.
        if "Groundskeeper" in available:
            names.append("Groundskeeper")

        names += ["Oasis"]

        # Junk Dealer is a cantrip, but only worth it while there is junk to
        # eat; otherwise it eats a card the deck wants.
        if any(self._junk_rank(c) is not None for c in player.hand):
            names.append("Junk Dealer")

        if "Cellar" in available and any(
            self._junk_rank(c) is not None for c in player.hand
        ):
            names.append("Cellar")

        names += ["Margrave", "Library", "Monument", "Moneylender"]

        names += ["Junk Dealer", "Cellar"]
        return self.pick(choices, names)

    # -- card decisions ------------------------------------------------
    @staticmethod
    def _junk_rank(card):
        """Rank junk worth discarding or trashing; ``None`` means keep."""
        if card.name == "Curse":
            return 0
        if card.name == "Estate":
            return 1
        if card.name == "Copper":
            return 2
        return None

    def choose_cards_to_discard(self, state, player, choices, count, *, reason=None):
        ranked = [
            (self._junk_rank(c), c) for c in choices if self._junk_rank(c) is not None
        ]
        ranked.sort(key=lambda item: (item[0], item[1].name))
        picks = [card for _, card in ranked[:count]]
        # The hook's contract is "choose *up to* ``count``" (``BaseAI``), so a
        # short list is a legal answer and, for an optional effect, the right
        # one: Cellar -- the only one of this board's ten piles that reaches
        # this hook at all -- is optional, and so are The Sun's Gift, Vault,
        # Hamlet, Marchland, Plaza, Sextant, Artificer, Quest, Capital City,
        # Cave Dwellers and Lost in the Woods. Filling the count there hands
        # away Provinces and Golds for nothing.
        #
        # ``reason`` is a flat namespace of effect names with no mandatory flag,
        # and Haunting and Sibyl reuse this hook to pick a card to *topdeck*.
        # So the default stays short, and only the named mandatory callers that
        # would otherwise under-discard get topped up.
        if reason not in _MANDATORY_DISCARDS or len(picks) >= count:
            return picks
        # Junk first (above), then the cheapest thing the deck can spare:
        # victory cards are dead in hand, engine pieces are not spare at all.
        chosen = {id(card) for card in picks}
        rest = [card for card in choices if id(card) not in chosen]
        rest.sort(
            key=lambda c: (
                not (c.is_victory and not c.is_action and not c.is_treasure),
                c.name in _ENGINE_PIECES,
                c.cost.coins,
                c.name,
            )
        )
        return picks + rest[: count - len(picks)]

    def choose_card_to_trash_with_junk_dealer(self, state, player, choices):
        if not choices:
            return None
        counts = Counter(c.name for c in player.all_cards())
        ranked = []
        for card in choices:
            rank = self._junk_rank(card)
            if rank is None:
                continue
            # Once only three Coppers are left the deck would rather eat an
            # Estate: Estates gained under Groundskeeper have already scored
            # their token, so trashing them afterwards is free.
            if card.name == "Copper" and counts["Copper"] <= 3:
                continue
            ranked.append((rank, card.name, card))
        if ranked:
            ranked.sort(key=lambda item: item[:2])
            return ranked[0][2]
        # Nothing junky is left to eat, and Junk Dealer's trash is not optional,
        # so give up the cheapest spare rather than an engine piece. That spare
        # is often one of the last Coppers: the floor above is a preference
        # between junk, not a hard reserve. Reserving those Coppers outright
        # was measured and costs win rate, because the only cards left to feed
        # Junk Dealer instead are Silvers, which are worth more than a Copper.
        spare = [c for c in choices if c.name not in _ENGINE_PIECES]
        pool = spare or list(choices)
        return min(pool, key=lambda c: (c.cost.coins, c.name))

    def should_trash_copper_for_moneylender(self, state, player):
        counts = Counter(c.name for c in player.all_cards())
        return counts["Copper"] > 3

    def should_keep_library_action(self, state, player, card):
        # Library puts a kept card in hand, it does not play it, and nothing on
        # this board grants Villagers. With no Actions left even a village is
        # dead weight that costs a replacement draw, so set every Action aside.
        return player.actions > 0

    # -- buys ----------------------------------------------------------
    # Border Village's on-gain pick reaches ``choose_gain`` too: it calls
    # ``player.ai.choose_buy``, which GeneticAI routes here.
    def choose_gain(self, state, player, choices):
        p = self.params
        available = {c.name: c for c in choices if c is not None}
        if not available:
            return None
        counts = Counter(c.name for c in player.all_cards())
        provinces = state.supply.get("Province", 8)
        # A free gain (Border Village) offers only cards cheaper than $6, so
        # the Province/Gold rungs simply will not match.
        names = []

        greening = player.turns_taken >= p["green"] or provinces <= 4
        # Each Groundskeeper played this turn adds a token per victory gain.
        groundskeeper_live = getattr(player, "groundskeeper_bonus", 0) > 0

        if greening:
            names.append("Province")
        if provinces <= p["duchy"] or (groundskeeper_live and greening):
            names.append("Duchy")
        if provinces <= 1:
            names.append("Estate")

        # Groundskeeper turns each extra green card into a VP token, so spare
        # buys go on Estates once it is actually in play.
        if p["estate_vp"] and groundskeeper_live and player.buys >= 1 and greening:
            names.append("Estate")

        if player.turns_taken <= 1 and p["opening"] and not counts[p["opening"]]:
            names.append(p["opening"])

        for name, cap in (
            ("Groundskeeper", p["groundskeeper"]),
            ("Margrave", p["margrave"]),
            ("Library", p["library"]),
            ("Junk Dealer", p["junk_dealer"]),
            ("Monument", p["monument"]),
            ("Moneylender", p["moneylender"]),
        ):
            if counts[name] >= cap:
                continue
            # Keep terminals behind the villages that support them.
            if name in ("Margrave", "Library", "Monument", "Moneylender"):
                villages = counts["Fishing Village"] + counts["Border Village"]
                terminals = (
                    counts["Margrave"]
                    + counts["Library"]
                    + counts["Monument"]
                    + counts["Moneylender"]
                )
                if terminals >= 1 and villages < terminals and self._terminals() > 1:
                    continue
            names.append(name)

        if counts["Border Village"] < p["border_village"]:
            names.append("Border Village")
        if counts["Fishing Village"] < p["fishing_village"]:
            names.append("Fishing Village")
        if counts["Gold"] < p["golds"]:
            names.append("Gold")
        if counts["Oasis"] < p["oasis"]:
            names.append("Oasis")
        if counts["Silver"] < p["silvers"]:
            names.append("Silver")
        if counts["Cellar"] < p["cellar"]:
            names.append("Cellar")

        names += ["Gold", "Silver"]
        return self.pick(choices, names)


def create_margrave_library_monument_engine() -> EnhancedStrategy:
    """Winner of the twelve-entrant finalist round robin on this board.

    Four Fishing Villages and two Border Villages support two Libraries and a
    Margrave; two Monuments supply the points, and two Junk Dealers eat the
    starting Coppers and Estates. Notably it buys no Groundskeeper: the search
    ranked every Groundskeeper plan below the Monument decks.
    """
    strategy = GroundskeeperMargrave(
        fishing_village=4,
        border_village=2,
        library=2,
        margrave=1,
        monument=2,
        junk_dealer=2,
        silvers=99,
        golds=3,
        green=12,
        duchy=4,
        estate_vp=True,
        opening="Silver",
    )
    strategy.name = "Margrave Library Monument Engine"
    strategy.description = (
        "Fishing Village and Border Village support Library and Margrave draw; "
        "two Monuments score the victory points and two Junk Dealers thin the "
        "starting deck. See the Groundskeeper Margrave board guide."
    )
    # Report only the cards this policy actually buys. The other board piles
    # belong to the search variants, not to this factory's plan.
    active = {
        "Fishing Village",
        "Border Village",
        "Library",
        "Margrave",
        "Monument",
        "Junk Dealer",
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

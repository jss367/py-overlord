"""Tunable policies for the Jerusalem board.

Kingdom: Goons, Sea Hag, Governor, Ambassador, Minion, Old Witch,
Scrying Pool, Fortress, Ill-Gotten Gains, Bridge Troll -- the ten cards no
registered strategy referenced when the board was assembled.

The search script records parameters and seeds. Only frozen finalists get
factories, so exploratory candidates do not inflate the public catalog.
"""

from collections import Counter

from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


DEFAULTS = dict(
    # Acquisition targets: the most copies the deck ever wants. Every kingdom
    # pile starts at zero so a plan built as ``DEFAULTS | dict(...)`` contains
    # exactly the cards it names -- an inherited count is a card in the deck
    # that nobody chose, and it silently rewrites what the plan is.
    goons=0, sea_hag=0, governor=0, ambassador=0, minion=0, old_witch=0,
    scrying_pool=0, fortress=0, igg=0, bridge_troll=0,
    potion=0, silver=99, gold=99,
    # Greening gates. ``green`` is a completed-turn count; ``duchy`` and
    # ``estate`` are Provinces-remaining thresholds.
    green=10, duchy=4, estate=2, green_first=True,
    # Openings.
    opening="Ambassador", first_five="Governor",
    # Which acquisition order to follow once the openings are bought.
    build="goons",
    # Play policies.
    governor_mode="auto", minion_mode="auto", pool_self="actions",
    ambassador_max=2, ambassador_curse=True, copper_floor=3,
    goons_filler=True, filler="Copper",
)

CARD_KEYS = {
    "Goons": "goons", "Sea Hag": "sea_hag", "Governor": "governor",
    "Ambassador": "ambassador", "Minion": "minion", "Old Witch": "old_witch",
    "Scrying Pool": "scrying_pool", "Fortress": "fortress",
    "Ill-Gotten Gains": "igg", "Bridge Troll": "bridge_troll",
    "Potion": "potion", "Silver": "silver", "Gold": "gold",
}

#: Acquisition orders once the opening buys are satisfied.
ORDERS = {
    "goons": ["Governor", "Fortress", "Goons", "Bridge Troll", "Old Witch",
              "Minion", "Ambassador", "Sea Hag", "Gold", "Silver"],
    "pool": ["Potion", "Scrying Pool", "Fortress", "Governor", "Goons",
             "Old Witch", "Minion", "Bridge Troll", "Ambassador", "Sea Hag",
             "Gold", "Silver"],
    "minion": ["Minion", "Fortress", "Governor", "Goons", "Old Witch",
               "Ambassador", "Sea Hag", "Bridge Troll", "Gold", "Silver"],
    "rush": ["Ill-Gotten Gains", "Sea Hag", "Old Witch", "Ambassador",
             "Governor", "Fortress", "Minion", "Goons", "Bridge Troll",
             "Gold", "Silver"],
    "money": ["Old Witch", "Sea Hag", "Ill-Gotten Gains", "Governor", "Minion",
              "Goons", "Ambassador", "Fortress", "Bridge Troll",
              "Gold", "Silver"],
}

# Silver and Gold close every order: their targets are usually unbounded, so
# anything listed after them would never be reached and the knob would look
# tuned while doing nothing.

#: Cards this family never wants to hand to Governor's trash-for-upgrade.
_ENGINE_PIECES = frozenset({
    "Goons", "Governor", "Fortress", "Scrying Pool", "Minion", "Bridge Troll",
    "Old Witch", "Sea Hag", "Potion",
})

_JUNK = ("Curse", "Estate", "Copper")


class Jerusalem(EnhancedStrategy):
    """One parameterized deck plan for the Jerusalem board."""

    def __init__(self, **params):
        super().__init__()
        unknown = set(params) - DEFAULTS.keys()
        if unknown:
            raise ValueError(f"Unknown parameters: {sorted(unknown)}")
        self.params = DEFAULTS | params
        self.name = "Jerusalem Search Candidate"
        self.description = (
            "Configurable Jerusalem policy: cursers, Fortress villages, and a "
            "choice of Goons, Scrying Pool, Minion, or Ill-Gotten Gains payload."
        )
        active = [
            name for name, key in CARD_KEYS.items()
            if self.params[key] or name in {self.params["opening"], self.params["first_five"]}
        ]
        self.gain_priority = [PriorityRule(n) for n in ["Province", "Duchy", "Estate"] + active]
        self.action_priority = [
            PriorityRule(n) for n in self._action_order() if n in active
        ]
        # Only the treasures this plan actually acquires, so the catalog's
        # card usage report does not credit a pile the deck never buys.
        # ``choose_treasure`` still knows the full order for a copy arriving
        # from somewhere else.
        self.treasure_priority = [
            PriorityRule(n)
            for n in ("Gold", "Silver", "Ill-Gotten Gains", "Potion", "Copper")
            if n in active or n == "Copper"
        ]
        self.trash_priority = [PriorityRule(n) for n in _JUNK]

    def _action_order(self):
        """Villages first, then draw, then the terminal attacks.

        Scrying Pool and Governor are non-terminal, so they run ahead of the
        one terminal the turn can afford. Goons sits last among the payload
        only when the deck cannot chain: its +$2 and +1 Buy are wanted in the
        buy phase either way, while Old Witch's +3 Cards can find more.
        """
        return ["Fortress", "Scrying Pool", "Minion", "Governor", "Old Witch",
                "Goons", "Bridge Troll", "Sea Hag", "Ambassador"]

    # ------------------------------------------------------------------ util

    @staticmethod
    def pick(choices, names):
        available = {c.name: c for c in choices if c is not None}
        return next((available[n] for n in names if n in available), None)

    @staticmethod
    def _junk_in(cards):
        return sum(1 for c in cards if c.name in _JUNK)

    def _sheddable(self, player):
        """Junk names this deck is currently willing to give up.

        Copper is economy until the deck has replaced it. Shedding below the
        floor is how an Ambassador deck talks itself down to six cards and
        never buys anything again, so the floor counts Coppers actually left.
        """
        names = ["Curse", "Estate"]
        if not self.params["ambassador_curse"]:
            names = ["Estate"]
        bought = sum(
            1 for c in player.all_cards()
            if c.is_treasure and c.name not in {"Copper", "Potion"}
        )
        floor = max(0, self.params["copper_floor"] - bought)
        if sum(1 for c in player.all_cards() if c.name == "Copper") > floor:
            names.append("Copper")
        return names

    def _greening(self, state, player):
        provinces = state.supply.get("Province", 8)
        return player.turns_taken >= self.params["green"] or provinces <= 4

    # --------------------------------------------------------------- choices

    def choose_action(self, state, player, choices):
        p = self.params
        names = ["Fortress"]
        # Ambassador is only worth an action while the hand holds something
        # this deck is actually willing to hand back.
        shed = set(self._sheddable(player))
        if p["ambassador"] and any(c.name in shed for c in player.hand):
            names.append("Ambassador")
        names += ["Scrying Pool", "Minion", "Governor"]
        # With one action left, spend it on the terminal that does the most.
        # Ambassador is deliberately absent here: revealing a card the deck
        # will not return hands the opponent a free copy of it.
        names += ["Old Witch", "Goons", "Bridge Troll", "Sea Hag"]
        return self.pick(choices, names)

    def choose_treasure(self, state, player, choices):
        return self.pick(
            choices, ["Gold", "Silver", "Ill-Gotten Gains", "Potion", "Copper"]
        )

    @staticmethod
    def _owner_of(state, player, choices):
        """The player whose hand the offered cards came from.

        ``GeneticAI.choose_card_to_trash`` has no player argument and passes
        ``state.current_player``. Governor asks every player in turn, so when
        this strategy answers an opponent's Governor that is the attacker,
        not the responder -- and an economy floor measured against the wrong
        deck sheds Coppers the responder needed. Resolve the owner from the
        cards themselves and fall back to the argument.
        """
        offered = [c for c in choices if c is not None]
        if not offered:
            return player
        for candidate in state.players:
            if any(card in candidate.hand for card in offered):
                return candidate
        return player

    def choose_trash(self, state, player, choices):
        """Ranked for Governor's upgrade: junk first, then a deliberate trade."""
        real = [c for c in choices if c is not None]
        if not real:
            return None
        player = self._owner_of(state, player, choices)
        pick = self.pick(real, self._sheddable(player))
        if pick is not None:
            return pick
        # Gold -> Province is the upgrade worth making; Silver -> $5 is next.
        pick = self.pick(real, ["Gold", "Silver"])
        if pick is not None and state.supply.get("Province", 8) <= 6:
            return pick
        if any(c is None for c in choices):
            return None
        return min(
            real,
            key=lambda c: (c.name in _ENGINE_PIECES, c.is_victory, c.cost.coins, c.name),
        )

    # ------------------------------------------------------------- card modes

    def choose_governor_option(self, state, player, options):
        mode = self.params["governor_mode"]
        if mode != "auto":
            return mode
        # Gold -> Province closes the game; Estate -> Fortress builds it.
        if state.supply.get("Province", 8) <= 6 and any(
            c.name == "Gold" for c in player.hand
        ):
            return "upgrade"
        if self._junk_in(player.hand) and not self._greening(state, player):
            return "upgrade"
        if self._greening(state, player) and state.supply.get("Gold", 0):
            return "gold"
        return "cards"

    def choose_minion_mode(self, state, player):
        mode = self.params["minion_mode"]
        if mode != "auto":
            return mode
        # Redraw a hand that is mostly junk or already spent; otherwise bank $2.
        if len(player.hand) <= 2 or self._junk_in(player.hand) >= 2:
            return "discard"
        return "coins"

    def choose_card_to_ambassador(self, state, player, choices):
        return self.pick(choices, self._sheddable(player))

    def choose_ambassador_return_count(self, state, player, revealed, maximum):
        if revealed.name not in _JUNK:
            return min(1, maximum)
        if revealed.name != "Copper":
            return min(self.params["ambassador_max"], maximum)
        # Never cross the economy floor in a single return.
        spare = sum(1 for c in player.all_cards() if c.name == "Copper") - (
            self.params["copper_floor"]
        )
        return max(0, min(self.params["ambassador_max"], maximum, spare))

    def choose_topdeck_or_discard(self, state, chooser, target, revealed, *, is_self):
        """True discards the revealed card, False leaves it on top."""
        if not is_self:
            # Strip an opponent's best card; leave their junk to draw.
            return revealed.name not in _JUNK
        if self.params["pool_self"] == "actions":
            # Scrying Pool draws the run of Actions on top, so anything else
            # on top both misses the draw and blocks it.
            return not revealed.is_action
        return revealed.name in _JUNK

    def choose_cards_to_discard(self, state, player, choices, count, reason=None):
        ranked = sorted(
            [c for c in choices if c is not None],
            key=lambda c: (
                c.name not in _JUNK,
                c.name in _ENGINE_PIECES,
                -c.is_victory,
                c.cost.coins,
            ),
        )
        return ranked[:count]

    # ----------------------------------------------------------------- buying

    def choose_gain(self, state, player, choices):
        p = self.params
        available = {c.name: c for c in choices if c is not None}
        if not available:
            return None
        counts = Counter(c.name for c in player.all_cards())
        provinces = state.supply.get("Province", 8)
        greening = self._greening(state, player)

        names = []
        if greening:
            names.append("Province")
        # A rush wants its payload pile ahead of the Duchies it is racing to;
        # an engine wants the Duchy the moment its gate opens.
        deferred = []
        target = names if p["green_first"] else deferred
        if provinces <= p["duchy"]:
            target.append("Duchy")
        if provinces <= p["estate"]:
            target.append("Estate")

        winner = self._winning_gain(state, player, available)
        if winner is not None:
            return winner

        if player.turns_taken <= 1:
            if state.phase == "buy" and player.coins >= 5:
                names.append(p["first_five"])
            if counts[p["opening"]] == 0:
                names.append(p["opening"])

        # A Potion is dead weight unless Scrying Pool is actually wanted.
        if p["scrying_pool"] and counts["Potion"] < p["potion"]:
            names.append("Potion")

        for name in ORDERS[p["build"]]:
            if counts[name] >= p[CARD_KEYS[name]]:
                continue
            if name == "Ill-Gotten Gains" and not self._igg_is_live(state):
                continue
            names.append(name)
        names += deferred
        if greening:
            names += ["Duchy", "Estate"]

        pick = self.pick(choices, names)
        if pick is not None:
            return pick
        filler = self._goons_filler(state, player, choices)
        if filler is not None:
            return filler
        if state.phase == "buy":
            return None
        # Not a buy: this is a free gain (Governor's upgrade), so declining
        # throws the card away. Take the best thing on offer instead.
        return self._best_free_gain(state, player, choices)

    def _best_free_gain(self, state, player, choices):
        real = [c for c in choices if c is not None]
        if not real:
            return None
        wanted = [n for n in ORDERS[self.params["build"]] if self.params[CARD_KEYS[n]]]
        rank = {name: i for i, name in enumerate(wanted)}

        def key(card):
            return (
                card.name == "Curse",
                card.is_victory and not card.is_action,
                rank.get(card.name, len(rank)),
                -card.cost.coins,
                card.name,
            )

        return min(real, key=key)

    @staticmethod
    def _igg_is_live(state):
        """Whether another Ill-Gotten Gains is worth $5.

        Its whole value is the Curse it hands out. Once the Curses are gone it
        is a $5 Copper, worth buying only as the last copy of a pile that
        helps end the game.
        """
        if state.supply.get("Curse", 0) > 0:
            return True
        return state.supply.get("Ill-Gotten Gains", 0) == 1

    def _winning_gain(self, state, player, available):
        """Take a pile-emptying gain that wins the game outright."""
        if len(state.players) != 2:
            return None
        empty = sum(
            v == 0 for k, v in state.supply.items()
            if k not in state.non_supply_pile_names
        )
        opponent = next(q for q in state.players if q is not player)
        lead = player.get_victory_points() - opponent.get_victory_points()
        winners = [
            c for c in available.values()
            if state.supply.get(c.name) == 1
            and (empty >= 2 or c.name == "Province")
            and lead + c.stats.vp > 0
        ]
        if not winners:
            return None
        return max(winners, key=lambda c: (c.stats.vp, c.cost.coins))

    def _goons_filler(self, state, player, choices):
        """Spend leftover buys on the cheapest card while Goons scores them.

        Each Goons in play turns any buy into a VP token, so a spare buy is
        worth a point even when nothing in the Supply improves the deck.
        """
        if not (self.params["goons_filler"] and player.goons_played):
            return None
        order = [self.params["filler"], "Copper", "Estate", "Curse"]
        return self.pick(choices, list(dict.fromkeys(order)))


def create_jerusalem_scrying_pool_goons() -> EnhancedStrategy:
    """Search winner: Scrying Pool draw, Fortress villages, Goons payload.

    Validated at 79.0% across 3,000 held-out games against ten opponents.
    """
    strategy = Jerusalem(
        scrying_pool=8, potion=1, fortress=5, goons=5, ambassador=1,
        bridge_troll=3, sea_hag=2, old_witch=1, silver=1, gold=0,
        green=99, duchy=3, estate=3, green_first=False, copper_floor=3,
        filler="Estate", opening="Potion", first_five="Old Witch", build="pool",
    )
    strategy.name = "Jerusalem Scrying Pool Goons"
    strategy.description = (
        "Open Potion, curse with Sea Hag and Old Witch, then draw the deck with "
        "eight Scrying Pools over five Fortresses and convert every spare buy "
        "into a point under five Goons. Greens only once four Provinces are gone."
    )
    return strategy


def create_jerusalem_curse_goons_money() -> EnhancedStrategy:
    """Best plan that builds no engine: double cursing plus Goons on money.

    The strongest money policy found on this board, and the yardstick the
    engine had to beat.
    """
    strategy = Jerusalem(
        sea_hag=1, old_witch=1, goons=2, silver=99, gold=99,
        green=0, duchy=4, estate=2, opening="Sea Hag", first_five="Old Witch",
        build="money",
    )
    strategy.name = "Jerusalem Curse Goons Money"
    strategy.description = (
        "Sea Hag and Old Witch empty the Curse pile, two Goons add points per "
        "buy, and the deck is otherwise Silver, Gold and immediate Provinces."
    )
    return strategy

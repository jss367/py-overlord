"""Mine-centred strategies for the Kimberley Colony board; parameters support search."""

from collections import Counter

from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


JUNK = ("Curse", "Estate", "Copper")
UPGRADE_TARGET = {"Copper": "Silver", "Silver": "Gold", "Gold": "Platinum"}


class KimberleyMine(EnhancedStrategy):
    """Climb Copper -> Silver -> Gold -> Platinum with Mine, multiplied by
    Throne Room and King's Court, while Sewers, Tomb, Priest, and Market
    Square pay out on every Treasure Mine trashes."""

    def __init__(
        self,
        *,
        opening="Mine",
        second="Priest",
        mines=2,
        kings=1,
        thrones=1,
        labs=2,
        smithies=0,
        villages=1,
        priests=1,
        squares=2,
        hoards=0,
        banks=0,
        platinums=9,
        golds=1,
        silvers=1,
        sewers=True,
        upgrade="climb",
        multiplier="mine",
        terminal_order="mine",
        keep_coppers=3,
        green_turn=14,
        province_colonies=4,
        kc_turn=4,
    ):
        super().__init__()
        self.name = "Kimberley Mine Engine"
        multipliers = [
            name
            for name, count in (("Throne Room", thrones), ("King's Court", kings))
            if count
        ]
        self.description = (
            "Mine climbs Copper to Silver to Gold to Platinum in hand"
            + (f", repeated by {' and '.join(multipliers)}" if multipliers else ", with no multipliers")
            + "; Sewers, Tomb, Priest, and Market Square pay out on each trash."
        )
        self.params = dict(
            opening=opening,
            second=second,
            mines=mines,
            kings=kings,
            thrones=thrones,
            labs=labs,
            smithies=smithies,
            villages=villages,
            priests=priests,
            squares=squares,
            hoards=hoards,
            banks=banks,
            platinums=platinums,
            golds=golds,
            silvers=silvers,
            sewers=sewers,
            upgrade=upgrade,
            multiplier=multiplier,
            terminal_order=terminal_order,
            keep_coppers=keep_coppers,
            green_turn=green_turn,
            province_colonies=province_colonies,
            kc_turn=kc_turn,
        )
        self.mine_gains = Counter()
        self.multiplier_targets = Counter()
        self.action_priority = [
            PriorityRule(n)
            for n in [
                "Mining Village",
                "Laboratory",
                "Market Square",
                "King's Court",
                "Throne Room",
                "Priest",
                "Mine",
                "Smithy",
            ]
        ]
        self.treasure_priority = [
            PriorityRule(n)
            for n in ["Platinum", "Gold", "Hoard", "Silver", "Copper", "Bank"]
        ]
        self.trash_priority = [
            PriorityRule("Curse"),
            PriorityRule("Estate"),
            PriorityRule(
                "Copper",
                lambda s, me: me.count("Copper") > self.params["keep_coppers"],
            ),
        ]
        self.gain_priority = [
            PriorityRule(n)
            for n in [
                "Colony",
                "Province",
                "Platinum",
                "King's Court",
                "Bank",
                "Hoard",
                "Gold",
                "Mine",
                "Laboratory",
                "Throne Room",
                "Priest",
                "Smithy",
                "Mining Village",
                "Market Square",
                "Sewers",
                "Duchy",
                "Silver",
                "Estate",
            ]
        ]

    @staticmethod
    def pick(choices, names):
        available = {c.name: c for c in choices if c is not None}
        return next((available[n] for n in names if n in available), None)

    # ------------------------------------------------------------------
    # Mine
    def _upgradeable(self, state, player, card):
        target = UPGRADE_TARGET.get(card.name)
        if target is None:
            p = self.params
            return False
        if target == "Platinum":
            return (
                state.supply.get("Platinum", 0) > 0
                and player.count("Platinum") < self.params["platinums"]
            )
        return state.supply.get(target, 0) > 0

    def _mine_has_work(self, state, player):
        return any(
            c.is_treasure and self._upgradeable(state, player, c) for c in player.hand
        )

    def choose_mine_treasure(self, state, player, choices):
        """Trash the Treasure whose upgrade is worth most right now."""
        p = self.params
        usable = [c for c in choices if self._upgradeable(state, player, c)]
        if p["upgrade"] == "copper":
            order = ["Copper", "Silver", "Gold"]
        elif p["upgrade"] == "silver":
            order = ["Silver", "Gold", "Copper"]
        else:  # climb: take the biggest step available
            order = ["Gold", "Silver", "Copper"]
        chosen = self.pick(usable, order)
        self.mine_source = chosen.name if chosen else None
        return chosen

    def choose_mine_gain(self, state, player, choices):
        p = self.params
        names = []
        if player.count("Platinum") < p["platinums"]:
            names.append("Platinum")
        if player.count("Bank") < p["banks"]:
            names.append("Bank")
        if player.count("Hoard") < p["hoards"]:
            names.append("Hoard")
        names += ["Gold", "Silver", "Copper"]
        chosen = self.pick(choices, names)
        if chosen:
            self.mine_gains[f"{getattr(self, 'mine_source', '?')} -> {chosen.name}"] += 1
        return chosen

    # ------------------------------------------------------------------
    # Actions
    def _has_junk(self, player):
        keep = self.params["keep_coppers"]
        return any(
            c.name in ("Curse", "Estate")
            or (c.name == "Copper" and player.count("Copper") > keep)
            for c in player.hand
        )

    def _playable(self, state, player, choices):
        """Drop Actions that would do nothing useful this turn."""
        result = []
        for c in choices:
            if c is None:
                result.append(c)
            elif c.name == "Mine" and not self._mine_has_work(state, player):
                continue
            elif c.name == "Priest" and not self._has_junk(player):
                continue
            else:
                result.append(c)
        return result

    def _multiplier_order(self, state, player):
        p = self.params
        draw = ["Smithy", "Laboratory"]
        mine = ["Mine"] if self._mine_has_work(state, player) else []
        priest = ["Priest"] if self._has_junk(player) else []
        if p["multiplier"] == "draw":
            names = draw + mine + priest
        elif p["multiplier"] == "priest":
            names = priest + mine + draw
        else:
            names = mine + draw + priest
        return names + ["King's Court", "Throne Room", "Market Square", "Mining Village"]

    def choose_action(self, state, player, choices):
        if not getattr(state, "_choosing_main_action_phase", False):
            # Throne Room / King's Court asks which Action to repeat.
            chosen = self.pick(choices, self._multiplier_order(state, player))
            if chosen:
                self.multiplier_targets[chosen.name] += 1
            return chosen
        p = self.params
        choices = self._playable(state, player, choices)
        terminals = ["Priest", "Mine", "Smithy"]
        if p["terminal_order"] == "priest":
            terminals = ["Priest", "Mine", "Smithy"]
        elif p["terminal_order"] == "smithy":
            terminals = ["Smithy", "Priest", "Mine"]
        else:
            terminals = ["Mine", "Priest", "Smithy"]
        multipliers = []
        if any(n in self._multiplier_order(state, player)[:3] for n in
               [c.name for c in choices if c is not None]):
            multipliers = ["King's Court", "Throne Room"]
        # A Priest before Mine turns Mine's trash into +$2, so with actions to
        # spare the Priest goes first regardless of the terminal order.
        lead = []
        if player.actions >= 2 and self._has_junk(player):
            lead = ["Priest"]
        order = (
            ["Mining Village", "Laboratory", "Market Square"]
            + multipliers
            + lead
            + terminals
        )
        return self.pick(choices, order)

    # ------------------------------------------------------------------
    # Buying
    def choose_gain(self, state, player, choices):
        p = self.params
        available = {c.name: c for c in choices if c is not None}
        if not available:
            return None
        # Mine's gain menu only contains Treasures and arrives outside the buy phase.
        if state.phase != "buy" and all(c.is_treasure for c in available.values()):
            return self.choose_mine_gain(state, player, choices)
        counts = Counter(c.name for c in player.all_cards())
        has_sewers = any(x.name == "Sewers" for x in player.projects)
        colonies = state.supply.get("Colony", 0)
        provinces = state.supply.get("Province", 8)
        names = []
        late = colonies <= p["province_colonies"] or player.turns_taken >= p["green_turn"]
        if counts["Platinum"] or late or player.turns_taken >= 8:
            names.append("Colony")
        if late:
            names.append("Province")
        if colonies <= 2:
            names.append("Duchy")
        if colonies <= 1:
            names.append("Estate")
        if player.turns_taken <= 2:
            if not counts[p["opening"]]:
                names.append(p["opening"])
            if not counts[p["second"]]:
                names.append(p["second"])
            names += ["Silver", "Market Square"]
            return self.pick(choices, names)
        if counts["Platinum"] < p["platinums"]:
            names.append("Platinum")
        if counts["King's Court"] < p["kings"] and player.turns_taken >= p["kc_turn"]:
            names.append("King's Court")
        if counts["Bank"] < p["banks"]:
            names.append("Bank")
        if counts["Hoard"] < p["hoards"]:
            names.append("Hoard")
        if counts["Gold"] < p["golds"]:
            names.append("Gold")
        if counts["Mine"] < p["mines"]:
            names.append("Mine")
        if counts["Laboratory"] < p["labs"]:
            names.append("Laboratory")
        terminals = counts["Mine"] + counts["Priest"] + counts["Smithy"]
        if counts["Mining Village"] < min(p["villages"], max(0, terminals - 1)):
            names.append("Mining Village")
        if counts["Throne Room"] < p["thrones"]:
            names.append("Throne Room")
        if counts["Priest"] < p["priests"]:
            names.append("Priest")
        if counts["Smithy"] < p["smithies"]:
            names.append("Smithy")
        if p["sewers"] and not has_sewers:
            names.append("Sewers")
        if counts["Market Square"] < p["squares"]:
            names.append("Market Square")
        if counts["Mining Village"] < p["villages"]:
            names.append("Mining Village")
        names.append("Gold")
        if counts["Silver"] < p["silvers"]:
            names.append("Silver")
        if player.turns_taken >= 10:
            names += ["Province", "Duchy"]
        return self.pick(choices, names)


def create_kimberley_mine_engine() -> EnhancedStrategy:
    """Best confirmed configuration: one Mine and no multipliers at all."""
    return KimberleyMine(opening="Mine", second="Priest", mines=1, kings=0, thrones=0)

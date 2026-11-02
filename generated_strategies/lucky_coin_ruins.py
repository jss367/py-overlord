"""Searchable policies for the Lucky Coin and five Ruins starting scenario."""

from collections import Counter

from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule

RUINS = (
    "Survivors",
    "Ruined Village",
    "Ruined Market",
    "Ruined Library",
    "Abandoned Mine",
)
KINGDOM = (
    "Daimyo",
    "Battle Plan",
    "Fool",
    "Secluded Shrine",
    "Change",
    "Spice Merchant",
    "Highwayman",
    "Lost City",
    "Mining Road",
    "Tea House",
)
START = ("Lucky Coin", *RUINS, "Copper", "Copper", "Copper", "Copper")


class LuckyCoinRuins(EnhancedStrategy):
    def __init__(
        self,
        *,
        opening="Secluded Shrine",
        second="Tea House",
        tea=5,
        lost=2,
        daimyo=4,
        shrine=1,
        change=0,
        spice=0,
        highway=0,
        mining=1,
        fool=0,
        battle=0,
        warlord=0,
        free="adaptive",
        green=2,
        banquet=True,
        money=False,
        double="adaptive",
        scrounge=False,
    ):
        super().__init__()
        self.name = "Lucky Coin Ruins Engine"
        self.description = "Buy Tea House or use Banquet, add Highwayman and Mining Road, and gain free Daimyos."
        self.p = dict(
            opening=opening,
            second=second,
            tea=tea,
            lost=lost,
            daimyo=daimyo,
            shrine=shrine,
            change=change,
            spice=spice,
            highway=highway,
            mining=mining,
            fool=fool,
            battle=battle,
            warlord=warlord,
            free=free,
            green=green,
            banquet=banquet,
            money=money,
            double=double,
            scrounge=scrounge,
        )
        self.gain_priority = [
            PriorityRule(n)
            for n in (
                *KINGDOM,
                "Warlord",
                "Archer",
                "Territory",
                "Province",
                "Gold",
                "Silver",
                "Duchy",
                "Estate",
                "Banquet",
                "Scrounge",
            )
        ]

    @staticmethod
    def pick(choices, names):
        cards = {c.name: c for c in choices if c is not None}
        return next((cards[n] for n in names if n in cards), None)

    def engine_order(self, s, p, *, hand=False):
        c = Counter(x.name for x in p.all_cards())
        h = Counter(x.name for x in p.hand)
        z = self.p
        names = []
        if z["shrine"] and not c["Secluded Shrine"] and sum(c[n] for n in RUINS) >= 2:
            names.append("Secluded Shrine")
        if hand and not h["Lost City"] and c["Lost City"] < z["lost"]:
            names.append("Lost City")
        if hand and z["free"] != "adaptive":
            names.append(
                {"tea": "Tea House", "daimyo": "Daimyo", "draw": "Lost City"}[z["free"]]
            )
        if c["Tea House"] < min(z["tea"], 2):
            names.append("Tea House")
        for n, cap in [
            ("Lost City", z["lost"]),
            ("Change", z["change"]),
            ("Spice Merchant", z["spice"]),
            ("Highwayman", z["highway"]),
            ("Mining Road", z["mining"]),
            ("Warlord", z["warlord"]),
            ("Battle Plan", z["battle"]),
            ("Fool", z["fool"]),
        ]:
            if c[n] < cap:
                names.append(n)
        if hand and c["Daimyo"] < z["daimyo"]:
            names.append("Daimyo")
        if c["Tea House"] < z["tea"]:
            names.append("Tea House")
        if c["Secluded Shrine"] < z["shrine"] and sum(c[n] for n in RUINS) >= 2:
            names.append("Secluded Shrine")
        return names

    def choose_kind_emperor_gain(self, s, p, choices):
        """Gain missing draw and engine components to hand, then free Daimyos."""
        return self.pick(
            choices,
            self.engine_order(s, p, hand=True)
            + [
                "Daimyo",
                "Tea House",
                "Lost City",
                "Mining Road",
                "Highwayman",
                "Battle Plan",
                "Change",
                "Spice Merchant",
                "Fool",
                "Secluded Shrine",
                "Archer",
                "Warlord",
            ],
        )

    def choose_free_gain(self, s, p, choices, context):
        """Use engine targets without buying another Event or taking debt."""
        names = self.engine_order(s, p)
        if self.p["money"]:
            names = ["Gold", "Tea House", "Highwayman"]
        return self.pick(
            choices,
            names + ["Tea House", "Lost City", "Gold", "Duchy", "Silver", "Estate"],
        )

    def choose_gain(self, s, p, choices):
        """Open with the configured setup, build the engine, and buy Provinces."""
        c = Counter(x.name for x in p.all_cards())
        z = self.p
        if s.phase != "buy":  # Change's mandatory more-expensive gain.
            names = ["Province"] if c["Tea House"] >= z["green"] else []
            return self.pick(
                choices,
                names
                + self.engine_order(s, p)
                + ["Province", "Gold", "Tea House", "Lost City", "Duchy", "Silver"],
            )
        names = []
        if c["Tea House"] >= z["green"] or s.supply["Province"] <= 4 or z["money"]:
            names.append("Province")
        if s.supply["Province"] <= 3:
            names.append("Duchy")
        if s.supply["Province"] <= 1:
            names.append("Estate")
        if p.turns_taken <= 2:
            if z["opening"] == "Banquet":
                names.append("Banquet")
            elif not c[z["opening"]]:
                names.append(z["opening"])
            if z["second"] == "Banquet" or (
                z["banquet"] and z["second"] == "Tea House"
            ):
                names += [z["second"], "Banquet"]
            else:
                names.append(z["second"])
        if z["money"]:
            if z["highway"] and not c["Highwayman"]:
                names.append("Highwayman")
            names += ["Gold", "Silver"]
        else:
            names += self.engine_order(s, p)
            if z["banquet"] and c["Tea House"] < z["tea"]:
                names.append("Banquet")
            names += ["Province", "Gold"]
            if c["Silver"] < 2:
                names.append("Silver")
        if s.supply["Province"] <= 5 and not s.supply["Tea House"]:
            names.append("Duchy")
        if z["scrounge"] and (
            any(x.name in RUINS for x in p.hand)
            or any(x.name == "Estate" for x in s.trash)
        ):
            names.append("Scrounge")
        return self.pick(choices, names)

    def choose_action(self, s, p, choices):
        """Play Daimyos before draw or income, then support and usable Ruins."""
        h = Counter(x.name for x in p.hand)
        names = ["Daimyo"]
        if p.daimyo_pending:
            if self.p["double"] == "highway":
                names.append("Highwayman")
            draw = self.p["double"] == "draw" or (
                self.p["double"] == "adaptive"
                and (sum(x.is_action for x in p.hand) > p.actions or len(p.hand) <= 5)
            )
            names += ["Lost City", "Tea House"] if draw else ["Tea House", "Lost City"]
        names += ["Lost City", "Tea House", "Mining Road", "Warlord"]
        if h["Copper"]:
            names.append("Spice Merchant")
        names += [
            "Change",
            "Highwayman",
            "Secluded Shrine",
            "Battle Plan",
            "Archer",
            "Fool",
        ]
        # Save the Ruins for Shrine if Lucky Coin can trigger it this turn.
        if not (
            h["Lucky Coin"]
            and any(getattr(x, "shrine_armed", False) for x in p.duration)
        ):
            names += [
                "Ruined Village",
                "Ruined Library",
                "Abandoned Mine",
                "Ruined Market",
                "Survivors",
            ]
        return self.pick(choices, names)

    def choose_treasure(self, s, p, choices):
        """Play Lucky Coin first, after absorbing Highwayman with a Copper."""
        # Absorb Highwayman's block with Copper before playing Lucky Coin.
        if p.highwayman_attacks and not p.highwayman_blocked_this_turn:
            return self.pick(choices, ["Copper", "Silver", "Lucky Coin", "Gold"])
        return self.pick(choices, ["Lucky Coin", "Gold", "Silver", "Copper"])

    def choose_trash(self, s, p, choices):
        """Trash Curses and Ruins, then Estates and affordable-to-lose Coppers."""
        junk = [
            "Curse",
            "Survivors",
            "Ruined Market",
            "Abandoned Mine",
            "Ruined Library",
            "Ruined Village",
            "Estate",
        ]
        # Preserve buying power early; remove Coppers once payload exists.
        if p.count_in_deck("Tea House") or p.count_in_deck("Silver") >= 3:
            junk.append("Copper")
        result = self.pick(choices, junk)
        if result is None and None not in choices and choices:
            result = min(choices, key=lambda c: (c.cost.coins, c.name))
        return result

    def choose_spice_merchant_mode(self, s, p):
        """Take two cards and an Action."""
        return "cards"

    def choose_allies_option(self, s, p, reason, options, default):
        """Rotate Clashes toward Warlord only when that family requests it."""
        if reason == "rotate_pile":
            if self.p["warlord"] and not p.count_in_deck("Warlord"):
                return next(
                    (
                        n
                        for n in options
                        if n is not None and n in ("Battle Plan", "Archer")
                    ),
                    None,
                )
            return None
        return default


def create_lucky_coin_ruins() -> EnhancedStrategy:
    """Selected before validation on fresh, seat-balanced seeds."""
    return LuckyCoinRuins(
        opening="Tea House",
        shrine=0,
        spice=0,
        lost=0,
        highway=1,
        green=1,
        double="adaptive",
        daimyo=2,
    )

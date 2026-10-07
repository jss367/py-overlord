"""Searchable policies for the Shepherd, Tragic Hero and Night-card kingdom."""

from collections import Counter

from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule

KINGDOM = (
    "Faithful Hound",
    "Guardian",
    "Herbalist",
    "Monastery",
    "Secret Cave",
    "Exorcist",
    "Shepherd",
    "Cobbler",
    "Crypt",
    "Tragic Hero",
)


class ShepherdTragicHero(EnhancedStrategy):
    def __init__(
        self,
        *,
        shepherd=1,
        hero=2,
        monastery=1,
        cave=0,
        hound=0,
        exorcist=0,
        cobbler=0,
        crypt=0,
        guardian=0,
        herbalist=0,
        silver=3,
        gold=99,
        green=0,
        duchy=3,
        estate=1,
        keep_estates=True,
        extra_estates=0,
        opening="Shepherd",
        priority="draw",
        imps=2,
        ghosts=0,
        cave_mode=0,
        crypt_min=2,
        monastery_timing="early",
        cobbler_shepherds=None,
        cobbler_estates=0,
        cobbler_silver=0,
        cobbler_adaptive=False,
    ):
        super().__init__()
        self.name = "Shepherd and Tragic Hero Search Policy"
        self.description = "Searchable draw, money, trashing and Spirit policies."
        self.params = dict(
            shepherd=shepherd,
            hero=hero,
            monastery=monastery,
            cave=cave,
            hound=hound,
            exorcist=exorcist,
            cobbler=cobbler,
            crypt=crypt,
            guardian=guardian,
            herbalist=herbalist,
            silver=silver,
            gold=gold,
            green=green,
            duchy=duchy,
            estate=estate,
            keep_estates=keep_estates,
            extra_estates=extra_estates,
            opening=opening,
            priority=priority,
            imps=imps,
            ghosts=ghosts,
            cave_mode=cave_mode,
            crypt_min=crypt_min,
            monastery_timing=monastery_timing,
            cobbler_shepherds=cobbler_shepherds,
            cobbler_estates=cobbler_estates,
            cobbler_silver=cobbler_silver,
            cobbler_adaptive=cobbler_adaptive,
        )
        self.action_priority = [
            PriorityRule(n)
            for n in (
                "Wish",
                "Will-o'-Wisp",
                "Shepherd",
                "Secret Cave",
                "Imp",
                "Tragic Hero",
                "Faithful Hound",
                "Herbalist",
            )
        ]
        self.treasure_priority = [
            PriorityRule(n)
            for n in ("Gold", "Silver", "Pasture", "Copper", "Magic Lamp")
        ]
        self.gain_priority = [
            PriorityRule(n)
            for n in ("Province", "Duchy", "Estate", "Gold", "Silver", *KINGDOM)
        ]

    @staticmethod
    def pick(choices, names):
        available = {c.name: c for c in choices if c is not None}
        return next((available[n] for n in names if n in available), None)

    def choose_action(self, state, player, choices):
        names = ["Wish", "Will-o'-Wisp"]
        if any(c.is_victory for c in player.hand):
            names.append("Shepherd")
        names += [
            "Secret Cave",
            "Shepherd",
            "Imp",
            "Tragic Hero",
            "Faithful Hound",
            "Herbalist",
        ]
        return self.pick(choices, names)

    def choose_imp_action(self, state, player, choices):
        return self.choose_action(state, player, choices)

    def choose_gain(self, state, player, choices):
        p = self.params
        c = Counter(card.name for card in player.all_cards())
        provinces = state.supply.get("Province", 8)
        names = []
        if player.turns_taken >= p["green"] or provinces <= 4:
            names.append("Province")
        if provinces <= p["duchy"]:
            names.append("Duchy")
        if provinces <= p["estate"]:
            names.append("Estate")
        opening_key = {
            "Shepherd": "shepherd",
            "Tragic Hero": "hero",
            "Monastery": "monastery",
            "Exorcist": "exorcist",
            "Silver": "silver",
        }.get(p["opening"])
        if (
            player.turns_taken <= 2
            and not c[p["opening"]]
            and opening_key
            and p[opening_key] > 0
        ):
            names.append(p["opening"])
        if (
            c["Monastery"] < p["monastery"]
            and player.turns_taken <= 8
            and p["monastery_timing"] == "early"
        ):
            names.append("Monastery")
        targets = [
            ("Shepherd", "shepherd"),
            ("Tragic Hero", "hero"),
            ("Cobbler", "cobbler"),
            ("Exorcist", "exorcist"),
            ("Crypt", "crypt"),
            ("Secret Cave", "cave"),
            ("Faithful Hound", "hound"),
            ("Guardian", "guardian"),
            ("Herbalist", "herbalist"),
        ]
        if p["priority"] == "night":
            targets.sort(key=lambda t: t[0] not in {"Cobbler", "Exorcist", "Crypt"})
        elif p["priority"] == "cave":
            targets.sort(key=lambda t: t[0] not in {"Secret Cave", "Faithful Hound"})
        elif p["priority"] == "money" and c["Gold"] < p["gold"]:
            names.append("Gold")
        for name, key in targets:
            cap = p[key]
            if name == "Crypt" and c["Gold"] == 0:
                continue
            if (
                name == "Shepherd"
                and c[name]
                and c[name] * 2 > sum(x.is_victory for x in player.all_cards())
            ):
                continue
            if c[name] < cap:
                names.append(name)
        if c["Gold"] < p["gold"]:
            names.append("Gold")
        if c["Silver"] < p["silver"]:
            names.append("Silver")
        if (
            c["Monastery"] < p["monastery"]
            and player.turns_taken <= 12
            and p["monastery_timing"] == "spare"
        ):
            names.append("Monastery")
        if c["Estate"] < p["extra_estates"] and c["Shepherd"]:
            names.append("Estate")
        return self.pick(choices, names)

    def choose_card_to_gain_to_hand(self, state, player, choices, max_cost):
        p = self.params
        # Cobbler is the only gain-to-hand effect capped at $4 on this board.
        # Wishes retain the original $6 gain policy.
        if max_cost != 4 or p["cobbler_shepherds"] is None:
            return self.choose_gain(state, player, choices) or self.pick(
                choices, ["Gold", "Silver", "Estate", "Copper"]
            )
        owned = Counter(card.name for card in player.all_cards())
        names = []
        if state.supply.get("Province", 8) <= p["estate"]:
            names.append("Estate")
        if owned["Silver"] < p["cobbler_silver"]:
            names.append("Silver")
        target = p["cobbler_shepherds"]
        need_shepherd = owned["Shepherd"] < target
        if p["cobbler_adaptive"]:
            need_shepherd &= any(card.is_victory for card in player.hand) and not any(
                card.name == "Shepherd" for card in player.hand
            )
        if need_shepherd:
            names.append("Shepherd")
        if owned["Estate"] < p["cobbler_estates"]:
            names.append("Estate")
        names += ["Silver", "Estate", "Shepherd", "Copper"]
        return self.pick(choices, names)

    def choose_treasure(self, state, player, choices):
        c = Counter(card.name for card in player.all_cards())
        available = list(choices)
        if (
            any(x.name == "Exorcist" for x in player.hand)
            and c["Imp"] < self.params["imps"]
            and c["Silver"] >= 1
        ):
            silvers = [x for x in player.hand if x.name == "Silver"]
            if silvers:
                available = [x for x in available if x is not silvers[0]]
        # Give Lamp a chance to see singleton Treasures before duplicate plays.
        played = {x.name for x in player.in_play + player.duration}
        if any(x.name == "Magic Lamp" for x in available):
            first = [
                x for x in available if x.name not in played and x.name != "Magic Lamp"
            ]
            if first:
                return self.pick(first, ["Gold", "Silver", "Pasture", "Copper"])
            return self.pick(available, ["Magic Lamp"])
        return self.pick(available, ["Gold", "Silver", "Pasture", "Copper"])

    def choose_night(self, state, player, choices):
        names = ["Guardian", "Cobbler"]
        if self.choose_trash(state, player, list(player.hand)) is not None:
            names.append("Exorcist")
        names += ["Monastery", "Crypt", "Ghost"]
        return self.pick(choices, names)

    def choose_trash(self, state, player, choices):
        c = Counter(card.name for card in player.all_cards())
        names = ["Curse"]
        if not self.params["keep_estates"] and state.supply.get("Province", 8) > 3:
            names.append("Estate")
        if c["Imp"] < self.params["imps"]:
            names += ["Silver", "Secret Cave"]
        if c["Ghost"] < self.params["ghosts"]:
            names += ["Cobbler", "Crypt", "Tragic Hero", "Gold"]
        names += ["Copper"]
        # Spare Estates can become Wisps without exhausting Shepherd fuel.
        if c["Estate"] > max(3 if self.params["keep_estates"] else 0, c["Shepherd"]):
            names.append("Estate")
        return self.pick(choices, names)

    def choose_card_to_gain_for_exorcist(self, state, player, trashed, choices):
        c = Counter(card.name for card in player.all_cards())
        names = ["Imp", "Will-o'-Wisp", "Ghost"]
        if c["Ghost"] < self.params["ghosts"]:
            names.insert(0, "Ghost")
        return self.pick(choices, names)

    def choose_cards_to_trash_for_monastery(self, state, player, choices, count):
        p = self.params
        c = Counter(card.name for card in player.all_cards())
        junk = [x for x in choices if x.name == "Curse"]
        junk += [x for x in choices if x.name == "Copper"]
        if not p["keep_estates"] and state.supply.get("Province", 8) > 3:
            junk += [x for x in choices if x.name == "Estate"]
        # Keep enough economy to avoid trashing into a stalled deck.
        if c["Gold"] * 3 + c["Silver"] * 2 < 3:
            junk = [x for x in junk if x.name != "Copper"]
        return junk[:count]

    def choose_secret_cave_discards(self, state, player):
        junk = [
            x
            for x in player.hand
            if x.name in {"Faithful Hound", "Curse", "Estate", "Duchy", "Province"}
        ]
        if self.params["cave_mode"]:
            junk += [x for x in player.hand if x.name == "Copper"]
        return junk[:3] if len(junk) >= 3 else []

    def choose_treasures_to_set_aside_for_crypt(self, state, player, treasures):
        return [x for x in treasures if x.stats.coins >= self.params["crypt_min"]]


def create_shepherd_tragic_hero_best_found() -> EnhancedStrategy:
    """Highest mean score in the 18,000-game finalist round robin."""
    strategy = ShepherdTragicHero(
        shepherd=1, hero=1, monastery=0, silver=99, keep_estates=True, estate=3
    )
    strategy.name = "Shepherd Tragic Hero Best Found"
    strategy.description = (
        "Original search baseline: one Shepherd and one Tragic Hero support Gold and Province purchases. "
        "Keep the starting Estates; buy Duchies and Estates with three Provinces left. "
        "The Cobbler and Shepherd comparison guide contains the stronger follow-up strategy."
    )
    active = {
        "Shepherd",
        "Tragic Hero",
        "Wish",
        "Magic Lamp",
        "Pasture",
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

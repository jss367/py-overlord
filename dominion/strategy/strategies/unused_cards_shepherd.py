"""Searchable policies for the randomly drawn Shepherd and Catacombs board."""

from collections import Counter

from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class UnusedCardsShepherd(EnhancedStrategy):
    def __init__(
        self,
        *,
        shepherd=3,
        village=2,
        draw=3,
        university=0,
        embassy=0,
        counting=0,
        bauble=1,
        fish=0,
        silvers=2,
        golds=3,
        green=0,
        estates=0,
        fairgrounds=False,
        forts=False,
        opening="Shepherd",
        duchy=3,
        guild=True,
    ):
        super().__init__()
        self.name = "Random Kingdom Shepherd and Catacombs"
        self.description = (
            "Shepherd cycling, Cursed Village actions, and Catacombs draw."
        )
        self.params = dict(
            shepherd=shepherd,
            village=village,
            draw=draw,
            university=university,
            embassy=embassy,
            counting=counting,
            bauble=bauble,
            fish=fish,
            silvers=silvers,
            golds=golds,
            green=green,
            estates=estates,
            fairgrounds=fairgrounds,
            forts=forts,
            opening=opening,
            duchy=duchy,
            guild=guild,
        )
        self.action_priority = [
            PriorityRule(n)
            for n in (
                "University",
                "Shepherd",
                "Cursed Village",
                "Garrison",
                "Catacombs",
                "Embassy",
                "Counting House",
                "Hill Fort",
                "Stronghold",
                "Tent",
                "Fishmonger",
            )
        ]
        self.treasure_priority = [
            PriorityRule(n)
            for n in (
                "Gold",
                "Silver",
                "Copper",
                "Pasture",
                "Potion",
                "Bauble",
            )
        ]
        self.gain_priority = [
            PriorityRule(n)
            for n in (
                "Province",
                "Duchy",
                "Estate",
                "Fairgrounds",
                "Gold",
                "Silver",
                "Copper",
                "Potion",
                "Bauble",
                "Fishmonger",
                "Shepherd",
                "Cursed Village",
                "Catacombs",
                "Embassy",
                "Counting House",
                "University",
                "Tent",
                "Garrison",
                "Hill Fort",
                "Stronghold",
                "Woodworkers' Guild",
            )
        ]

    @staticmethod
    def pick(choices, names):
        available = {c.name: c for c in choices if c is not None}
        return next((available[n] for n in names if n in available), None)

    def choose_action(self, state, player, choices):
        available = {c.name for c in choices if c is not None}
        names = ["University"]
        if any(c.is_victory for c in player.hand):
            names.append("Shepherd")
        # Draw-to-six after spending cards when there are actions to spare.
        if player.actions <= 1 or len(player.hand) <= 5:
            names.append("Cursed Village")
        names += ["Shepherd", "Garrison", "Catacombs", "Embassy", "Cursed Village"]
        if (
            "Counting House" in available
            and sum(c.name == "Copper" for c in player.discard) >= 3
        ):
            names.insert(1 if player.actions > 1 else len(names), "Counting House")
        names += ["Hill Fort", "Stronghold", "Counting House", "Tent", "Fishmonger"]
        return self.pick(choices, names)

    def choose_bauble_options(self, state, player, options, count):
        if self.params["guild"] and player.favors < 1:
            return ["coin", "favor"]
        return ["coin", "buy"]

    def choose_allies_option(self, state, player, reason, options, default):
        if reason == "rotate_pile":
            return (
                "Tent"
                if self.params["forts"]
                and state.top_supply_card("Tent") != "Stronghold"
                else None
            )
        if reason == "woodworkers_trash":
            if not self.params["guild"]:
                return None
            # Trade a terminal left unplayed for a draw card or a village.
            return self.pick(
                options, ["Fishmonger", "Tent", "Counting House", "Embassy"]
            )
        return default

    def choose_gain(self, state, player, choices):
        p = self.params
        cards = list(player.all_cards())
        c = Counter(card.name for card in cards)
        available = {card.name: card for card in choices if card is not None}
        if not available:
            return None
        free_action = all(card.is_action for card in available.values())
        provinces = state.supply.get("Province", 8)
        names = []
        if not free_action:
            ready = player.turns_taken >= p["green"] or provinces <= 4
            if ready:
                names.append("Province")
            if provinces <= p["duchy"]:
                names.append("Duchy")
            if provinces <= 1:
                names.append("Estate")
            if p["fairgrounds"] and len(c) >= 14 and player.turns_taken >= 10:
                names.insert(0, "Fairgrounds")
            if p["university"] and c["Potion"] == 0 and player.turns_taken <= 6:
                names.append("Potion")
            if player.turns_taken <= 2 and not c[p["opening"]]:
                names.append(p["opening"])
        if c["University"] < p["university"]:
            names.append("University")
        if p["forts"] and c["Stronghold"] < 3:
            names.append("Stronghold")
        if c["Cursed Village"] < p["village"] and (
            c["Cursed Village"] == 0
            or c["Catacombs"] + c["Embassy"] >= c["Cursed Village"]
        ):
            names.append("Cursed Village")
        if c["Shepherd"] < p["shepherd"] and (
            c["Shepherd"] == 0 or sum(x.is_victory for x in cards) >= 2 * c["Shepherd"]
        ):
            names.append("Shepherd")
        for name, cap in [
            ("Catacombs", p["draw"]),
            ("Embassy", p["embassy"]),
            ("Counting House", p["counting"]),
        ]:
            if c[name] < cap:
                names.append(name)
        if c["Gold"] < p["golds"]:
            names.append("Gold")
        if c["Silver"] < p["silvers"]:
            names.append("Silver")
        if p["forts"] and c["Tent"] == 0:
            names.append("Tent")
        if c["Bauble"] < p["bauble"]:
            names.append("Bauble")
        if c["Fishmonger"] < p["fish"]:
            names.append("Fishmonger")
        if c["Estate"] < p["estates"] and c["Shepherd"] >= 2:
            names.append("Estate")
        if p["fairgrounds"] and player.turns_taken >= 8:
            names += [
                n
                for n in (
                    "Fairgrounds",
                    "Duchy",
                    "Tent",
                    "Garrison",
                    "Hill Fort",
                    "Stronghold",
                    "Fishmonger",
                    "Bauble",
                    "Embassy",
                    "Counting House",
                    "Potion",
                )
                if c[n] == 0
            ]
        if p["counting"] >= 2 and player.turns_taken >= 5 and c["Copper"] < 24:
            names.append("Copper")
        names += ["Gold", "Silver"]
        if free_action:
            names += ["Catacombs", "Shepherd", "Cursed Village"]
        return self.pick(choices, names)


def create_random_kingdom_shepherd_embassy_money() -> EnhancedStrategy:
    """Winner of the eight-policy, 5,600-game finalist round robin."""
    strategy = UnusedCardsShepherd(
        shepherd=1,
        village=0,
        draw=0,
        bauble=1,
        silvers=99,
        golds=99,
        opening="Embassy",
        embassy=1,
    )
    strategy.name = "Random Kingdom Shepherd Embassy Money"
    strategy.description = (
        "One Shepherd and one Embassy support Gold and Province buying, "
        "with one Bauble for spare buys. See the Random Unused Card Kingdom guide."
    )
    # Expose the winning policy's actual references in the catalog. Other
    # cards belong to the search variants, rather than this factory's plan.
    active = {
        "Shepherd",
        "Embassy",
        "Bauble",
        "Woodworkers' Guild",
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

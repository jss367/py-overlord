"""Parameterized plans for Collection, Imperial Envoy and Swindler."""

from collections import Counter

from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class CollectionImperialEnvoy(EnhancedStrategy):
    def __init__(
        self,
        *,
        collection=3,
        envoy=2,
        village=4,
        swindler=1,
        ghost=0,
        sleigh=0,
        fish=1,
        mystic=0,
        ship=0,
        forts=0,
        silver=2,
        gold=2,
        green=10,
        duchy=3,
        farm=2,
        opening="Swindler",
        first_five="Collection",
        cheap_first=False,
    ):
        super().__init__()
        self.params = {
            k: v for k, v in locals().items() if k not in {"self", "__class__"}
        }
        self.name = "Collection and Imperial Envoy"
        self.description = "Villages and Imperial Envoys support Collection scoring and Swindler attacks."
        self.action_priority = [
            PriorityRule(n)
            for n in (
                "Village",
                "Horse",
                "Mystic",
                "Garrison",
                "Imperial Envoy",
                "Swindler",
                "Hill Fort",
                "Sleigh",
                "Merchant Ship",
                "Stronghold",
                "Tent",
                "Fishmonger",
            )
        ]
        self.treasure_priority = [
            PriorityRule(n) for n in ("Collection", "Gold", "Silver", "Copper")
        ]
        self.gain_priority = [
            PriorityRule(n)
            for n in (
                "Province",
                "Duchy",
                "Collection",
                "Imperial Envoy",
                "Village",
                "Swindler",
                "Ghost Town",
                "Sleigh",
                "Fishmonger",
                "Mystic",
                "Merchant Ship",
                "Tent",
                "Garrison",
                "Hill Fort",
                "Stronghold",
                "Gold",
                "Silver",
                "Estate",
            )
        ]

    @staticmethod
    def pick(choices, names):
        available = {c.name: c for c in choices if c is not None}
        return next((available[n] for n in names if n in available), None)

    def choose_allies_option(self, state, player, reason, options, default):
        if reason == "rotate_pile":
            target = {1: "Garrison", 2: "Hill Fort", 3: "Stronghold"}.get(
                self.params["forts"]
            )
            return (
                "Tent" if target and state.top_supply_card("Tent") != target else None
            )
        return default

    def name_card_for_mystic(self, state, player):
        # Track remaining composition, never inspect the hidden top-card order.
        counts = Counter(c.name for c in player.all_cards())
        visible = {
            id(c): c
            for c in player.hand + player.in_play + player.duration + player.discard
        }
        for c in visible.values():
            counts[c.name] -= 1
        if not any(n > 0 for n in counts.values()):
            counts = Counter(c.name for c in player.discard)
        return max(sorted(counts), key=counts.get, default="Copper")

    def choose_swindler_replacement(self, state, player, target, choices):
        return self.pick(
            choices,
            [
                "Curse",
                "Estate",
                "Duchy",
                "Tent",
                "Silver",
                "Fishmonger",
                "Merchant Ship",
                "Mystic",
                "Swindler",
                "Ghost Town",
                "Village",
                "Garrison",
                "Hill Fort",
                "Sleigh",
                "Gold",
                "Stronghold",
                "Imperial Envoy",
                "Collection",
                "Province",
                "Copper",
            ],
        ) or (choices[0] if choices else None)

    def choose_gain(self, state, player, choices):
        p = self.params
        c = Counter(x.name for x in player.all_cards())
        provinces = state.supply.get("Province", 8)
        names = []
        if provinces <= 2 or player.turns_taken >= p["green"]:
            names.append("Province")
        if provinces <= p["duchy"]:
            names.append("Duchy")
        if provinces <= 1:
            names.append("Estate")
        if player.turns_taken <= 2 and not c[p["opening"]]:
            names.append(p["opening"])
        if not c["Collection"] and not c["Imperial Envoy"]:
            cap = p["collection"] if p["first_five"] == "Collection" else p["envoy"]
            if cap:
                names.append(p["first_five"])
        if c["Swindler"] < p["swindler"]:
            names.append("Swindler")
        if c["Imperial Envoy"] < p["envoy"] and (
            not c["Imperial Envoy"]
            or c["Village"] + c["Ghost Town"] >= c["Imperial Envoy"]
        ):
            names.append("Imperial Envoy")
        if c["Collection"] < p["collection"]:
            names.append("Collection")
        if (
            c["Village"] < p["village"]
            and c["Village"]
            <= c["Imperial Envoy"] + c["Swindler"] + c["Sleigh"] + c["Merchant Ship"]
        ):
            names.append("Village")
        for name, key in (
            ("Mystic", "mystic"),
            ("Merchant Ship", "ship"),
            ("Ghost Town", "ghost"),
            ("Sleigh", "sleigh"),
        ):
            if c[name] < p[key]:
                names.append(name)
        if p["forts"]:
            if not c["Tent"]:
                names.append("Tent")
            for name in ("Stronghold", "Hill Fort", "Garrison"):
                if c[name] < 2:
                    names.append(name)
        if p["farm"] and player.collection_played >= p["farm"]:
            names += (
                ["Fishmonger", "Sleigh", "Village", "Swindler", "Tent"]
                if p["cheap_first"]
                else ["Village", "Fishmonger", "Sleigh", "Swindler", "Tent"]
            )
        if c["Gold"] < p["gold"]:
            names.append("Gold")
        if c["Silver"] < p["silver"]:
            names.append("Silver")
        if c["Fishmonger"] < p["fish"]:
            names.append("Fishmonger")
        if provinces <= 3:
            names += ["Duchy", "Estate"]
        return self.pick(choices, names)


def create_collection_swindler_rush() -> EnhancedStrategy:
    """Winner of the 15-policy, 21,000-game finalist round robin."""
    strategy = CollectionImperialEnvoy(
        collection=4, envoy=0, farm=1, green=12, swindler=2, village=2
    )
    strategy.name = "Collection Swindler Rush"
    strategy.description = (
        "Two Swindlers into four Collections, scoring with repeated Village and "
        "Fishmonger purchases; skip Imperial Envoy and start Provinces on turn twelve."
    )
    return strategy

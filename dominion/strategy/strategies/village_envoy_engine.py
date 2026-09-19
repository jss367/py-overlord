"""Dedicated, interleaved Village / Imperial Envoy engine construction."""

from collections import Counter

from dominion.strategy.enhanced_strategy import EnhancedStrategy
from dominion.strategy.strategies.collection_imperial_envoy import (
    CollectionImperialEnvoy,
)


class VillageEnvoyEngine(CollectionImperialEnvoy):
    def __init__(
        self,
        *,
        envoy=3,
        village=5,
        collection=5,
        swindler=1,
        ghost=0,
        fish=0,
        silver=1,
        gold=0,
        mystic=0,
        ship=0,
        opening="Swindler",
        second="Silver",
        first_five="Imperial Envoy",
        order="balanced",
        green=99,
        farm_turn=10,
        farm_collections=2,
        cheap_first=False,
        spare_actions=1,
        min_draw=2,
        attack_first=True,
        adaptive_draw=False,
        gold_core=False,
    ):
        settings = {k: v for k, v in locals().items() if k not in {"self", "__class__"}}
        super().__init__()
        self.engine_params = settings
        self.name = "Village Imperial Envoy Engine"
        self.description = "Interleaved Village, Imperial Envoy and Collection construction with selective drawing and token purchases."

    def choose_action(self, state, player, choices):
        """Play Village, Horse, Mystic and Garrison before terminal Actions.

        When attack-first is enabled and more than one Action remains, play
        Swindler and Merchant Ship before drawing. Otherwise draw first.
        Skip Imperial Envoy below the configured remaining-card threshold.
        Then play Swindler, Merchant Ship, Hill Fort, Sleigh, Stronghold,
        Tent and Fishmonger in that order. Stop if no listed card is eligible.
        """
        p = self.engine_params
        remaining = len(player.deck) + len(player.discard)
        names = ["Village", "Horse", "Mystic", "Garrison"]
        if player.actions > 1 and p["attack_first"]:
            names += ["Swindler", "Merchant Ship"]
        # Drawing an empty deck charges debt without gaining cards. With few
        # cards left, a tunable cutoff trades the extra Buy against that debt.
        if remaining >= p["min_draw"]:
            names.append("Imperial Envoy")
        names += [
            "Swindler",
            "Merchant Ship",
            "Hill Fort",
            "Sleigh",
            "Stronghold",
            "Tent",
            "Fishmonger",
        ]
        return self.pick(choices, names)

    def choose_gain(self, state, player, choices):
        """Interleave income and draw instead of completing one target first.

        Buy Province from the configured turn or with two remaining; Duchy
        with two remaining and Estate with one. During opening turns, prefer
        the first-five card, then missing opening targets, Silver, Fishmonger.
        Afterward prioritize the first five-cost card, missing Swindlers,
        action support and Ghost Town. Order remaining engine targets by
        fraction already owned, adjusted for the selected income/draw bias.
        Once scoring starts, prioritize Collection and up to two Envoys,
        then repeated Village/Fishmonger/Sleigh purchases in the configured
        order. Finish with capped Gold, Silver, Fishmonger; then Swindler and
        Tent when scoring. Every purchase must be affordable and exposed.
        """
        p = self.engine_params
        cards = player.all_cards()
        c = Counter(x.name for x in cards)
        provinces = state.supply.get("Province", 8)
        names = []
        if player.turns_taken >= p["green"] or provinces <= 2:
            names.append("Province")
        if provinces <= 2:
            names.append("Duchy")
        if provinces <= 1:
            names.append("Estate")
        if player.turns_taken <= 2:
            # Do not waste a $5 opening on a $3 target.
            names.append(p["first_five"])
            if not c[p["opening"]]:
                names.append(p["opening"])
            elif not c[p["second"]]:
                names.append(p["second"])
            names += ["Silver", "Fishmonger"]
            return self.pick(choices, names)
        if not c["Collection"] and not c["Imperial Envoy"]:
            names.append(p["first_five"])
        if c["Swindler"] < p["swindler"]:
            names.append("Swindler")
        # Extra action support comes before another terminal, but acquisition
        # must start with a productive draw/income card rather than villages.
        terminals = c["Imperial Envoy"] + c["Swindler"] + c["Merchant Ship"]
        if (
            c["Village"] < p["village"]
            and c["Village"] + c["Ghost Town"] / 2 < terminals - 1 + p["spare_actions"]
        ):
            names.append("Village")
        if c["Ghost Town"] < p["ghost"] and c["Imperial Envoy"]:
            names.append("Ghost Town")
        envoy_target = p["envoy"]
        if p["adaptive_draw"]:
            # Each Village replaces itself; each Envoy nets four cards.
            envoy_target = min(
                envoy_target, max(1, (len(cards) - 5 - c["Village"] + 3) // 4)
            )
        # Interleave entire engine construction: unlike the original fixed
        # cap policy, do not buy all Envoys before building Collection income.
        targets = {
            "Imperial Envoy": envoy_target,
            "Collection": p["collection"],
            "Village": p["village"],
            "Mystic": p["mystic"],
            "Merchant Ship": p["ship"],
            "Gold": p["gold"] if p["gold_core"] else 0,
        }
        offsets = {
            "balanced": (0, 0),
            "income": (1, 0),
            "draw": (0, 1),
            "income_heavy": (2, 0),
        }[p["order"]]
        core = []
        for name in (
            "Imperial Envoy",
            "Collection",
            "Village",
            "Mystic",
            "Merchant Ship",
            "Gold",
        ):
            if targets[name] and c[name] < targets[name]:
                progress = c[name] / targets[name]
                if name == "Imperial Envoy":
                    progress += offsets[0] / targets[name]
                if name in {"Collection", "Gold"}:
                    progress += offsets[1] / targets[name]
                core.append((progress, name))
        core.sort(key=lambda x: x[0])
        # Build at least one Envoy and two Collections before unrestricted
        # point purchases, then vary when the engine switches to scoring.
        ready = c["Imperial Envoy"] >= 1 and c["Collection"] >= 2
        farm = (
            ready
            and player.turns_taken >= p["farm_turn"]
            and player.collection_played >= p["farm_collections"]
        )
        if not farm:
            names += [name for _, name in core]
        else:
            if c["Collection"] < p["collection"]:
                names.append("Collection")
            if c["Imperial Envoy"] < envoy_target and c["Imperial Envoy"] < 2:
                names.append("Imperial Envoy")
            names += (
                ["Fishmonger", "Sleigh", "Village"]
                if p["cheap_first"]
                else ["Village", "Fishmonger", "Sleigh"]
            )
        if c["Gold"] < p["gold"]:
            names.append("Gold")
        if c["Silver"] < p["silver"]:
            names.append("Silver")
        if c["Fishmonger"] < p["fish"]:
            names.append("Fishmonger")
        if farm:
            names += ["Swindler", "Tent"]
        return self.pick(choices, names)


class SelectiveEnvoyEngine(CollectionImperialEnvoy):
    """Keep the earlier buying policy while improving terminal play decisions."""

    def __init__(self, *, min_draw=1, attack_first=False, **kwargs):
        super().__init__(**kwargs)
        self.engine_params = dict(min_draw=min_draw, attack_first=attack_first)
        self.search_params = dict(
            self.params, min_draw=min_draw, attack_first=attack_first
        )
        self.name = "Selective Imperial Envoy Engine"

    def choose_action(self, state, player, choices):
        """Use the dedicated engine's selective draw and terminal-play order.

        Skip Envoy below the remaining-card cutoff. Village, Horse, Mystic
        and Garrison go first; optionally spend spare Actions on Swindler
        and Merchant Ship before Envoy. Other Actions follow after drawing.
        """
        return VillageEnvoyEngine.choose_action(self, state, player, choices)


def create_selective_envoy_collection() -> EnhancedStrategy:
    """Frozen dedicated-search finalist; see the Collection and Swindler guide."""
    strategy = SelectiveEnvoyEngine(
        collection=4, envoy=1, village=6, ghost=0, swindler=2, green=99, farm=1
    )
    strategy.name = "Selective Envoy Collection"
    return strategy


def create_village_envoy_collection_engine() -> EnhancedStrategy:
    """Frozen dedicated-search finalist; see the Collection and Swindler guide."""
    strategy = SelectiveEnvoyEngine(
        collection=6, envoy=2, village=6, ghost=2, swindler=2, green=99, farm=1
    )
    strategy.name = "Village Envoy Collection Engine"
    return strategy

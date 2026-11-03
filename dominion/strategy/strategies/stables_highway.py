"""Searchable deck plans for the Stables, Highway and Margrave kingdom."""

from collections import Counter

from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule

CARDS = ("Develop", "Guard Dog", "Weaver", "Cartographer", "Haggler", "Highway",
         "Inn", "Margrave", "Stables", "Witch's Hut")
KEYS = ("develop", "dog", "weaver", "cartographer", "haggler", "highway",
        "inn", "margrave", "stables", "hut")


class StablesHighway(EnhancedStrategy):
    def __init__(self, *, develop=0, dog=0, weaver=0, cartographer=0, haggler=0,
                 highway=0, inn=0, margrave=0, stables=0, hut=0, silver=3,
                 gold=99, green=0, duchy=4, opening="Silver", order="draw",
                 curse=True, gain_silver=4, terminal_limit=1):
        super().__init__()
        self.name = "Stables Highway Search"
        self.description = "Tunable Stables draw, Highway discounts and Margrave extra buys."
        self.params = {k: v for k, v in locals().items() if k not in {"self", "__class__"}}
        self.caps = dict(zip(CARDS, (self.params[k] for k in KEYS)))
        self.action_priority = [PriorityRule(n) for n in CARDS]
        self.treasure_priority = [PriorityRule(n) for n in ("Gold", "Silver", "Copper")]
        self.gain_priority = [PriorityRule(n) for n in ("Province", *CARDS, "Gold", "Silver", "Duchy", "Estate")]

    @staticmethod
    def pick(choices, names):
        available = {c.name: c for c in choices if c is not None}
        return next((available[n] for n in names if n in available), None)

    def choose_action(self, state, player, choices):
        names = ["Inn", "Highway", "Cartographer"]
        if any(c.is_treasure for c in player.hand):
            names.append("Stables")
        if any(c.name in {"Curse", "Estate", "Copper"} for c in player.hand):
            names.append("Develop")
        names += ["Margrave", "Guard Dog", "Witch's Hut", "Haggler", "Weaver"]
        # Develop's mandatory trash is avoidable by declining to play it.
        return self.pick(choices, names)

    def choose_trash(self, state, player, choices):
        junk = {"Curse": 0, "Estate": 1, "Copper": 2}
        return min(choices, key=lambda c: (junk.get(c.name, 10), c.cost.coins, c.name)) if choices else None

    def choose_cards_to_discard(self, state, player, choices, count, *, reason=None):
        if reason == "witchs_hut" and self.params["curse"] and state.supply.get("Curse", 0):
            actions = [c for c in choices if c.is_action]
            if len(actions) >= 2:
                return sorted(actions, key=lambda c: (c.name != "Weaver", c.name not in {"Develop", "Guard Dog"}, c.cost.coins))[:2]
        def rank(c):
            if c.name == "Weaver":
                return -1
            if c.name == "Curse" or (c.is_victory and not c.is_action):
                return 0
            if c.name == "Copper":
                return 1
            # After Margrave, preserve a playable draw chain and some fuel.
            if c.name in {"Develop", "Witch's Hut", "Haggler", "Guard Dog"}:
                return 2
            return 3 + c.cost.coins / 10
        return sorted(choices, key=rank)[:count]

    def _targets(self, player, counts):
        p = self.params
        # Interleave draw and support rather than collecting every copy of a
        # terminal before its village. All these priorities are searched.
        if p["order"] == "highway":
            order = ["Highway", "Stables", "Margrave", "Inn", "Haggler", "Witch's Hut", "Cartographer", "Guard Dog", "Weaver", "Develop"]
        elif p["order"] == "attack":
            order = ["Margrave", "Witch's Hut", "Stables", "Inn", "Highway", "Haggler", "Cartographer", "Guard Dog", "Weaver", "Develop"]
        else:
            order = ["Stables", "Margrave", "Inn", "Highway", "Haggler", "Witch's Hut", "Cartographer", "Guard Dog", "Weaver", "Develop"]
        names = []
        # First copies before bulk construction.
        for first in (True, False):
            for name in order:
                if counts[name] >= self.caps[name] or (counts[name] == 0) != first:
                    continue
                terminals = sum(counts[n] for n in ("Margrave", "Haggler", "Guard Dog", "Witch's Hut", "Weaver"))
                if name in {"Margrave", "Haggler", "Witch's Hut", "Guard Dog"} and terminals >= counts["Inn"] + p["terminal_limit"]:
                    continue
                names.append(name)
        return names

    def _gain(self, state, player, choices, free=False):
        p = self.params
        counts = Counter(c.name for c in player.all_cards())
        provinces = state.supply.get("Province", 8)
        names = []
        if player.turns_taken >= p["green"] or provinces <= 4:
            names.append("Province")
        if provinces <= p["duchy"]:
            names.append("Duchy")
        if provinces <= 1:
            names.append("Estate")
        if not free and player.turns_taken <= 1 and not counts[p["opening"]]:
            names.append(p["opening"])
        names += self._targets(player, counts)
        if counts["Gold"] < p["gold"]:
            names.append("Gold")
        if counts["Silver"] < p["silver"]:
            names.append("Silver")
        return self.pick(choices, names)

    def choose_gain(self, state, player, choices):
        return self._gain(state, player, choices)

    def choose_free_gain(self, state, player, choices, context):
        counts = Counter(c.name for c in player.all_cards())
        if context.source == "Weaver" and counts["Silver"] < self.params["gain_silver"]:
            return None  # The two-Silvers mode.
        pick = self._gain(state, player, choices, free=True)
        if pick is None and context.mandatory:
            return self.pick(choices, ("Gold", "Silver", "Copper", "Estate"))
        return pick


RECOMMENDED_PARAMETERS = {'duchy': 4,
 'margrave': 2,
 'opening': 'auto',
 'silver': 99,
 'terminal_limit': 2}


def create_stables_highway_best_found() -> EnhancedStrategy:
    """Frozen round-robin winner, evaluated on independent validation seeds."""
    strategy = StablesHighway(**RECOMMENDED_PARAMETERS)
    strategy.name = "Stables Highway Best Found"
    strategy.description = (
        "Two Margraves backed by Gold and uncapped Silver buying. Buy Provinces "
        "whenever affordable, Duchies at four Provinces remaining, and Estates "
        "at one. Open Silver/Silver on 4/3, or Margrave/pass on 5/2."
    )
    active = {"Margrave", "Gold", "Silver", "Copper", "Province", "Duchy", "Estate"}
    for attr in ("action_priority", "gain_priority", "treasure_priority"):
        setattr(strategy, attr, [rule for rule in getattr(strategy, attr) if rule.card in active])
    return strategy

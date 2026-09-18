"""Parameterized policies for the Stables, Ninja and Museum Colony kingdom."""
from collections import Counter

from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule

KINGDOM = ("Catapult", "Watchtower", "Conclave", "Harbor Village", "Innkeeper",
           "Ninja", "Silk Merchant", "Figurine", "Pendant", "Stables")


class StablesNinjaMuseum(EnhancedStrategy):
    """Build draw and attack, then diverse Treasures and Colony scoring."""

    def __init__(self, *, opening="Ninja", second="Catapult", stables=4,
                 silks=2, villages=2, ninjas=1, catapults=1, watchtowers=1,
                 conclaves=1, innkeepers=0, figurines=1, pendants=3,
                 silvers=2, golds=1, platinums=2, green_turn=17,
                 province_at=4, credit=False, curse_silver=False,
                 keep_copper=3, money=False, museum=True, ninja_first=False):
        super().__init__()
        self.name = "Stables Ninja Museum Engine"
        self.description = "Stables draw, Ninja pressure, Catapult thinning and diverse Treasures for Colony and Museum points."
        self.params = dict(opening=opening, second=second, stables=stables,
                           silks=silks, villages=villages, ninjas=ninjas,
                           catapults=catapults, watchtowers=watchtowers,
                           conclaves=conclaves, innkeepers=innkeepers,
                           figurines=figurines, pendants=pendants,
                           silvers=silvers, golds=golds, platinums=platinums,
                           green_turn=green_turn, province_at=province_at,
                           credit=credit, curse_silver=curse_silver,
                           keep_copper=keep_copper, money=money, museum=museum,
                           ninja_first=ninja_first)
        self.credit_target = None
        # Museum scores diversity at game end and is never gained, so nothing
        # in the priority lists names it; the searched buy order below only
        # makes sense on a board that has it.
        self.landscapes = ["Museum"]
        self.action_priority = [PriorityRule(n) for n in KINGDOM]
        self.gain_priority = [PriorityRule(n) for n in (*KINGDOM, "Platinum", "Colony", "Province", "Gold", "Silver", "Credit")]
        self.treasure_priority = [PriorityRule(n) for n in
                                 ("Figurine", "Platinum", "Gold", "Silver", "Rocks", "Copper", "Pendant")]

    @staticmethod
    def pick(choices, names):
        available = {c.name: c for c in choices if c is not None}
        return next((available[n] for n in names if n in available), None)

    def choose_action(self, state, player, choices):
        available = {c.name: c for c in choices if c is not None}
        names = ["Harbor Village"]
        if self.params["ninja_first"]:
            names.append("Ninja")
        if "Conclave" in available and any(
            c.is_action and c.name != "Conclave"
            and not any(x.name == c.name for x in player.in_play)
            for c in player.hand
        ):
            names.append("Conclave")
        if len(player.hand) <= 5:
            names.append("Watchtower")
        if any(c.is_treasure for c in player.hand):
            names.append("Stables")
        names += ["Innkeeper", "Silk Merchant", "Ninja"]
        if self.choose_trash(state, player, player.hand) is not None:
            names.append("Catapult")
        names.append("Conclave")
        return self.pick(choices, names)

    def choose_treasure_to_discard_for_stables(self, state, player, choices):
        if not player.deck and not player.discard:
            return None
        return self.pick(choices, ["Copper", "Rocks", "Silver", "Figurine", "Pendant", "Gold", "Platinum"])

    def choose_trash(self, state, player, choices):
        p = self.params
        names = ["Curse", "Estate"]
        if p["curse_silver"] and state.supply.get("Curse", 0):
            names += ["Rocks", "Silver"]
        if player.count("Copper") > p["keep_copper"]:
            names.append("Copper")
        if player.count("Silk Merchant") > 1 and state.supply.get("Curse", 0):
            names.append("Silk Merchant")
        return self.pick(choices, names)

    def choose_cards_to_discard(self, state, player, choices, count, reason=""):
        # Preserve a village/draw starter when attacked; spare Copper feeds Stables.
        values = {"Curse": -5, "Estate": -4, "Duchy": -4, "Province": -4,
                  "Colony": -4, "Copper": 1, "Silver": 3, "Gold": 5,
                  "Platinum": 7, "Pendant": 4, "Figurine": 5,
                  "Catapult": 4, "Ninja": 3, "Silk Merchant": 6,
                  "Conclave": 7, "Harbor Village": 8, "Watchtower": 9,
                  "Innkeeper": 5, "Stables": 8}
        has_treasure = any(c.is_treasure for c in choices)
        def value(c):
            v = values.get(c.name, 2)
            if c.name == "Stables" and not has_treasure:
                v = 0
            return v
        return sorted(choices, key=value)[:count]

    def choose_card_modes(self, state, player, card, options, minimum, maximum, defaults):
        if card.name == "Innkeeper":
            junk = sum(c.is_victory or c.name == "Curse" for c in player.hand)
            return ["sift3" if junk >= 2 or len(player.hand) <= 2 else "card"]
        return defaults

    def choose_watchtower_reaction(self, state, player, gained_card):
        if gained_card.name == "Curse":
            # A first Curse is +1 net Museum point only at the very end.
            if state.supply.get("Colony", 8) <= 1 and not player.count("Curse"):
                return None
            return "trash"
        if gained_card.is_victory or gained_card.name == "Copper":
            return None
        return "topdeck"

    def choose_gain(self, state, player, choices):
        p = self.params
        c = Counter(card.name for card in player.all_cards())
        available = {x.name: x for x in choices if x is not None}
        if self.credit_target is not None:
            target, self.credit_target = self.credit_target, None
            return available.get(target)
        names = []
        if player.turns_taken <= 2:
            if "Stables" in available and p["stables"]:
                names.append("Stables")
            if c[p["opening"]] == 0:
                names.append(p["opening"])
            if c[p["second"]] == 0:
                names.append(p["second"])
            choice = self.pick(choices, names)
            if choice:
                return choice
            if p["credit"] and "Credit" in available:
                self.credit_target = p["opening"] if not c[p["opening"]] else "Stables"
                return available["Credit"]
            return available.get("Silver")
        colonies = state.supply.get("Colony", 8)
        late = colonies <= 2 or state.supply.get("Province", 8) <= 2
        names = ["Colony"]
        if colonies <= p["province_at"] or player.turns_taken >= p["green_turn"]:
            names.append("Province")
        if late:
            names.append("Duchy")
        if c["Platinum"] < p["platinums"]:
            names.append("Platinum")
        # Get the first attack and trashing card before building duplicate draw.
        for n, cap in (("Ninja", p["ninjas"]), ("Catapult", p["catapults"]),
                       ("Watchtower", p["watchtowers"])):
            if c[n] < min(1, cap):
                names.append(n)
        if p["money"] and c["Gold"] < p["golds"]:
            names.append("Gold")
        if c["Stables"] < p["stables"]:
            names.append("Stables")
        terminals = c["Ninja"] + c["Catapult"] + c["Silk Merchant"] + c["Watchtower"]
        if c["Harbor Village"] < min(p["villages"], max(0, terminals - 1)):
            names.append("Harbor Village")
        for n, cap in (("Silk Merchant", p["silks"]), ("Conclave", p["conclaves"]),
                       ("Innkeeper", p["innkeepers"]), ("Ninja", p["ninjas"]),
                       ("Catapult", p["catapults"])):
            if c[n] < cap:
                names.append(n)
        for n, cap in (("Figurine", p["figurines"]), ("Gold", p["golds"]),
                       ("Pendant", p["pendants"]), ("Silver", p["silvers"])):
            if c[n] < cap:
                names.append(n)
        if p["museum"] and (late or player.turns_taken >= p["green_turn"]):
            names += [n for n in (*KINGDOM, "Rocks", "Gold", "Silver", "Estate", "Copper", "Curse") if not c[n]]
        if late:
            names.append("Estate")
        return self.pick(choices, names)


def create_ninja_watchtower_figurine_money() -> EnhancedStrategy:
    """Best policy selected by the recorded board search, before validation."""
    strategy = StablesNinjaMuseum(
        opening="Ninja", second="Watchtower", stables=0, silks=0, villages=0,
        catapults=0, conclaves=0, figurines=3, pendants=5, silvers=3, golds=2,
    )
    strategy.name = "Ninja Watchtower Figurine Money"
    strategy.description = (
        "Open Ninja and Watchtower, build three Figurines, then diverse Treasures "
        "and Platinum; score Colonies and collect Museum diversity late."
    )
    return strategy

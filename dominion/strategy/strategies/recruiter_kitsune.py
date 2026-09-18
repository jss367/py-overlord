"""Tunable policies for Recruiter / Kitsune with Great Leader.

The search script records parameters and seeds. Only frozen finalists have
factories, so exploratory candidates do not inflate the public catalog.
"""

from collections import Counter

from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


DEFAULTS = dict(
    recruiter=1, kitsune=2, inventor=3, treasurer=1, villa=2, village=0,
    courtyard=4, counterfeit=0, anvil=0, engineer=0, silver=2, gold=2,
    green=10, duchy=4, opening="Inventor", first_five="Recruiter",
    build="draw", engineer_trash=False, key_first=True, rescue=True,
)
CARD_KEYS = {
    "Recruiter": "recruiter", "Kitsune": "kitsune", "Inventor": "inventor",
    "Treasurer": "treasurer", "Villa": "villa", "Village": "village",
    "Courtyard": "courtyard", "Counterfeit": "counterfeit", "Anvil": "anvil",
    "Engineer": "engineer", "Silver": "silver", "Gold": "gold",
}


class RecruiterKitsune(EnhancedStrategy):
    def __init__(self, **params):
        super().__init__()
        unknown = set(params) - DEFAULTS.keys()
        if unknown:
            raise ValueError(f"Unknown parameters: {sorted(unknown)}")
        self.params = DEFAULTS | params
        self.name = "Recruiter Kitsune Search Candidate"
        self.description = "Courtyard draw, Recruiter thinning, and configurable gains and economy."
        active = [n for n, k in CARD_KEYS.items() if self.params[k]
                  or n in {self.params["opening"], self.params["first_five"]}]
        self.gain_priority = [PriorityRule(n) for n in ["Province", "Duchy", "Estate"] + active]
        self.action_priority = [PriorityRule(n) for n in active if n not in {"Gold", "Silver", "Counterfeit", "Anvil"}]
        self.treasure_priority = [PriorityRule(n) for n in ["Counterfeit", "Anvil", "Gold", "Silver", "Copper"] if n in active or n == "Copper"]
        self.trash_priority = [PriorityRule(n) for n in ("Curse", "Estate", "Copper")]

    @staticmethod
    def pick(choices, names):
        available = {c.name: c for c in choices if c is not None}
        return next((available[n] for n in names if n in available), None)

    @staticmethod
    def leader(state):
        return bool(state.prophecy and state.prophecy.name == "Great Leader" and state.prophecy.is_active)

    def choose_action(self, state, player, choices):
        names = ["Village", "Villa"]
        # The action has already been spent when card effects run, but here
        # it has not: preserve the last action with Kitsune before activation.
        if not self.leader(state) and player.actions <= 1:
            names.append("Kitsune")
        if any(c.name in {"Curse", "Estate", "Copper"} for c in player.hand):
            names.append("Recruiter")
        # Courtyard grows hand size; a Recruiter without junk is held back
        # until draw has had an opportunity to find an expendable card.
        names += ["Courtyard", "Kitsune", "Inventor", "Engineer", "Treasurer"]
        if any(c.name in {"Curse", "Estate", "Copper", "Silver"} for c in player.hand):
            names.append("Recruiter")
        return self.pick(choices, names)

    def choose_treasure(self, state, player, choices):
        return self.pick(choices, ["Counterfeit", "Anvil", "Gold", "Silver", "Copper"])

    def choose_trash(self, state, player, choices):
        pick = self.pick(choices, ["Curse", "Estate", "Copper", "Silver"])
        if pick:
            return pick
        # Optional trash effects include None; keep valuable cards when allowed.
        if not choices or None in choices:
            return None
        counts = Counter(c.name for c in player.all_cards())
        return min(choices, key=lambda c: (c.name in {"Province", "Duchy"}, counts[c.name] <= 1, c.cost.coins))

    def choose_card_modes(self, state, player, card, options, minimum, maximum, defaults):
        if card.name == "Kitsune":
            modes = []
            if not self.leader(state) and player.actions == 0 and any(c.is_action for c in player.hand):
                modes.append("action")
            if state.supply.get("Curse", 0):
                modes.append("curse")
            modes += ["coins", "action", "silver"]
            return list(dict.fromkeys(modes))[:maximum]
        if card.name == "Treasurer":
            key = state.artifacts.get("Key")
            if self.params["key_first"] and key and key.holder is not player:
                return ["key"]
            if any(c.name in {"Gold", "Counterfeit", "Anvil"} for c in state.trash):
                return ["gain"]
            if any(c.name == "Copper" for c in player.hand):
                return ["trash"]
            if key and key.holder is not player:
                return ["key"]
            if any(c.name == "Silver" for c in state.trash):
                return ["gain"]
            return ["key"]
        return defaults

    def choose_card_to_topdeck_for_courtyard(self, state, player, choices):
        can_continue = self.leader(state) or player.actions > 0 or player.villagers > 0
        if not can_continue:
            action = self.pick(choices, ["Recruiter", "Kitsune", "Courtyard", "Inventor", "Treasurer", "Engineer"])
            if action:
                return action
        # Put dead cards back, keeping playable draw and economy this turn.
        return min(choices, key=lambda c: (
            0 if c.name == "Curse" else 1 if c.is_victory else
            2 if c.name == "Copper" else 3 if c.name == "Silver" else
            4 if c.name in {"Village", "Villa"} and self.leader(state) else 5,
            c.cost.coins,
        )) if choices else None

    def should_trash_engineer_for_extra_gains(self, state, player, engineer):
        return self.params["engineer_trash"] or state.supply.get("Province", 8) <= 3

    def should_replay_treasure_with_counterfeit(self, state, player, choices):
        copper = self.pick(choices, ["Copper"])
        if copper:
            return copper
        if state.supply.get("Province", 8) <= 3 or any(c.name == "Treasurer" for c in player.all_cards()):
            return self.pick(choices, ["Gold", "Silver", "Anvil"])
        return None

    def choose_anvil_treasure_to_discard(self, state, player, choices):
        return self.pick(choices, ["Copper", "Silver"])

    def choose_anvil_gain(self, state, player, choices):
        return self.choose_gain(state, player, choices)

    def choose_gain(self, state, player, choices):
        p = self.params
        available = {c.name: c for c in choices if c is not None}
        if not available:
            return None
        # Treasurer's recovery presents actual cards from the trash.
        if all(c in state.trash for c in available.values()):
            return self.pick(choices, ["Gold", "Counterfeit", "Anvil", "Silver", "Copper"])
        counts = Counter(c.name for c in player.all_cards())
        provinces = state.supply.get("Province", 8)
        greening = player.turns_taken >= p["green"] or provinces <= 4
        names = []
        if greening:
            names.append("Province")
        if provinces <= p["duchy"]:
            names.append("Duchy")
        if provinces <= 2:
            names.append("Estate")
        # Catch an immediate winning pile ending, including a free gain.
        empty = sum(v == 0 for k, v in state.supply.items() if k not in state.non_supply_pile_names)
        if len(state.players) == 2:
            opponent = next(q for q in state.players if q is not player)
            lead = player.get_victory_points() - opponent.get_victory_points()
            winners = [c for c in available.values() if
                       (state.supply.get(c.name) == 1 and (empty >= 2 or c.name == "Province"))
                       and lead + c.stats.vp > 0]
            if winners:
                return max(winners, key=lambda c: (c.stats.vp, c.cost.coins))
        if player.turns_taken <= 1:
            # The opening is fixed per price, independent of hand order.
            if state.phase == "buy" and player.coins >= 5:
                names.append(p["first_five"])
            if counts[p["opening"]] == 0:
                names.append(p["opening"])
        # Villa gained to hand supplies an action even when Inventor spent
        # the last one. Buying one can also rescue unplayed draw immediately.
        draw_in_hand = any(c.name in {"Courtyard", "Recruiter", "Inventor", "Engineer"} for c in player.hand)
        rescue = (p["rescue"] and p["villa"] and draw_in_hand and
                  ((state.phase == "buy") or
                   (state.phase == "action" and player.actions == 0 and player.villagers == 0 and not self.leader(state))))
        if rescue:
            names.append("Villa")
        if counts[p["first_five"]] == 0 and p[CARD_KEYS[p["first_five"]]]:
            names.append(p["first_five"])
        for name in ("Recruiter", "Kitsune", "Treasurer"):
            if counts[name] == 0 and p[CARD_KEYS[name]]:
                names.append(name)
        orders = {
            "draw": ["Courtyard", "Inventor", "Kitsune", "Treasurer", "Recruiter", "Counterfeit", "Engineer", "Anvil", "Villa", "Village", "Gold", "Silver"],
            "gain": ["Inventor", "Engineer", "Courtyard", "Kitsune", "Treasurer", "Recruiter", "Villa", "Counterfeit", "Anvil", "Village", "Gold", "Silver"],
            "money": ["Treasurer", "Kitsune", "Counterfeit", "Gold", "Recruiter", "Courtyard", "Silver", "Inventor", "Engineer", "Anvil", "Villa", "Village"],
        }
        for name in orders[p["build"]]:
            if counts[name] >= p[CARD_KEYS[name]]:
                continue
            if name == "Engineer" and state.phase == "buy" and player.coins < 3:
                continue
            names.append(name)
        if greening:
            names += ["Duchy", "Estate"]
        return self.pick(choices, names)


def create_recruiter_kitsune_courtyard_engine() -> EnhancedStrategy:
    """Best aggregate score in the fixed-board twelve-policy round robin."""
    strategy = RecruiterKitsune(courtyard=8, first_five="Kitsune", opening="Silver")
    strategy.name = "Recruiter Kitsune Courtyard Engine"
    strategy.description = (
        "Great Leader board: open Silver/Courtyard, take Kitsune at the first $5, "
        "then Recruiter and Treasurer. Contest Courtyards, add Inventor and Villa, "
        "and prioritize Provinces after ten completed turns or four Provinces remain."
    )
    return strategy


def create_recruiter_kitsune_counterfeit_money() -> EnhancedStrategy:
    """Runner-up: immediate Province buying with Counterfeit and Courtyard."""
    strategy = RecruiterKitsune(
        courtyard=8, opening="Silver", inventor=2, counterfeit=1, villa=0,
        gold=4, silver=99, green=0, duchy=3, build="money",
    )
    strategy.name = "Recruiter Kitsune Counterfeit Money"
    strategy.description = (
        "Great Leader board: Recruiter first, Kitsune and Treasurer, then "
        "Counterfeit and Gold ahead of Courtyard draw; buy Provinces immediately."
    )
    return strategy


def create_recruiter_kitsune_six_courtyards() -> EnhancedStrategy:
    """Close engine rival with a six-Courtyard acquisition target."""
    strategy = RecruiterKitsune(courtyard=6, first_five="Kitsune", opening="Silver")
    strategy.name = "Recruiter Kitsune Six Courtyards"
    strategy.description = (
        "Great Leader board: the Courtyard engine with a six-copy draw target, "
        "switching to Inventor sooner if Courtyards remain available."
    )
    return strategy

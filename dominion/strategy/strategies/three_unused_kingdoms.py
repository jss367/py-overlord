"""Searchable policies for three kingdoms of previously unreferenced cards.

The recorded search, rather than the defaults here, selects published factories.
Only cards actually requested by a policy appear in its catalog priorities.
"""

from collections import Counter

from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


KINGDOMS = {
    "sentry_hunting_party": (
        "Bazaar",
        "Hunting Party",
        "Sentry",
        "Merchant",
        "Poacher",
        "Candlestick Maker",
        "Conspirator",
        "Bureaucrat",
        "Artisan",
        "Vassal",
    ),
    "minion_courtier": (
        "Minion",
        "Courtier",
        "Diplomat",
        "Baron",
        "Shanty Town",
        "Secret Passage",
        "Replace",
        "Trading Post",
        "Conclave",
        "Native Village",
    ),
    "old_witch_rabble": (
        "Old Witch",
        "Rabble",
        "Recruiter",
        "Silk Merchant",
        "Spices",
        "Squire",
        "Caravan",
        "Warehouse",
        "Haggler",
        "Soothsayer",
    ),
}

ACTION_ORDER = {
    "sentry_hunting_party": (
        "Bazaar",
        "Candlestick Maker",
        "Sentry",
        "Merchant",
        "Poacher",
        "Hunting Party",
        "Conspirator",
        "Artisan",
        "Vassal",
        "Bureaucrat",
    ),
    "minion_courtier": (
        "Native Village",
        "Shanty Town",
        "Secret Passage",
        "Conclave",
        "Diplomat",
        "Courtier",
        "Minion",
        "Trading Post",
        "Replace",
        "Baron",
    ),
    "old_witch_rabble": (
        "Squire",
        "Caravan",
        "Warehouse",
        "Recruiter",
        "Old Witch",
        "Rabble",
        "Silk Merchant",
        "Soothsayer",
        "Haggler",
    ),
}


class UnusedKingdomPolicy(EnhancedStrategy):
    """Ordered deck targets with tunable opening, greening and money density."""

    def __init__(
        self,
        board,
        *,
        targets=(),
        opening="Silver",
        silver=99,
        gold=99,
        green=0,
        duchy=3,
        minion_redraw=3,
        attack_first=True,
    ):
        super().__init__()
        self.board = board
        self.params = dict(
            targets=[list(t) for t in targets],
            opening=opening,
            silver=silver,
            gold=gold,
            green=green,
            duchy=duchy,
            minion_redraw=minion_redraw,
            attack_first=attack_first,
        )
        self.name = board.replace("_", " ").title()
        self.description = (
            "Best-found policy from the three previously unused kingdoms search."
        )
        active = {name for name, cap in targets if cap > 0}
        if opening in KINGDOMS[board]:
            active.add(opening)
        self.action_priority = [
            PriorityRule(n) for n in ACTION_ORDER[board] if n in active
        ]
        self.gain_priority = [
            PriorityRule(n)
            for n in dict.fromkeys(
                [
                    "Province",
                    "Duchy",
                    "Estate",
                    *[n for n, _ in targets],
                    opening,
                    "Gold",
                    "Silver",
                ]
            )
        ]
        self.treasure_priority = [
            PriorityRule(n)
            for n in ("Spices", "Gold", "Silver", "Copper")
            if n != "Spices" or n in active
        ]
        self.trash_priority = [PriorityRule(n) for n in ("Curse", "Estate", "Copper")]

    @staticmethod
    def pick(choices, names):
        available = {c.name: c for c in choices if c is not None}
        return next((available[n] for n in names if n in available), None)

    def choose_gain(self, state, player, choices):
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
        if player.turns_taken <= 2 and not counts[p["opening"]]:
            names.append(p["opening"])
        for name, cap in p["targets"]:
            if counts[name] < cap:
                names.append(name)
        if counts["Gold"] < p["gold"]:
            names.append("Gold")
        if counts["Silver"] < p["silver"]:
            names.append("Silver")
        # A legal optional pass is preferable to buying Copper or early Estate.
        return self.pick(choices, names)

    def choose_action(self, state, player, choices):
        names = list(ACTION_ORDER[self.board])
        if self.board == "minion_courtier":
            if len(player.hand) <= 4:
                names.remove("Diplomat")
                names.insert(0, "Diplomat")
            if any(c.name == "Estate" for c in player.hand):
                names.remove("Baron")
                names.insert(0 if player.actions > 1 else 4, "Baron")
            # Spend the other Minions for coins before the last redraw.
            if sum(c.name == "Minion" for c in player.hand) > 1:
                names.remove("Minion")
                names.insert(0, "Minion")
        if self.board == "old_witch_rabble":
            if self.params["attack_first"] and state.supply.get("Curse", 0) > 0:
                names.remove("Old Witch")
                names.insert(2, "Old Witch")
            # Recruiter is mandatory: avoid feeding it a useful deck when clean.
            if not any(
                c.name in {"Curse", "Estate", "Copper", "Silk Merchant"}
                for c in player.hand
            ):
                names.remove("Recruiter")
        if not any(c.name in {"Curse", "Estate", "Copper"} for c in player.hand):
            names = [n for n in names if n not in {"Trading Post", "Replace"}]
        return self.pick(choices, names)

    def choose_trash(self, state, player, choices):
        names = ["Curse", "Estate", "Copper"]
        if self.board == "old_witch_rabble":
            names.append("Silk Merchant")
        return self.pick(choices, names)

    def choose_cards_to_discard(self, state, player, choices, count, reason=None):
        return sorted(
            choices,
            key=lambda c: (
                0
                if c.name == "Curse" or c.is_victory
                else 1
                if c.name == "Copper"
                else 2,
                c.cost.coins,
                c.name,
            ),
        )[:count]

    def choose_minion_mode(self, state, player):
        treasure = sum(c.stats.coins for c in player.hand if c.is_treasure)
        if any(c.name == "Minion" for c in player.hand):
            return "coins"
        if player.coins + treasure + 2 >= 8:
            return "coins"
        return "discard" if treasure <= self.params["minion_redraw"] else "coins"

    def choose_courtier_options(self, state, player, options, num_choices):
        priority = ["coins", "gold", "buy", "action"]
        if player.actions == 0 and any(c.is_action for c in player.hand):
            priority = ["action", "coins", "gold", "buy"]
        return [n for n in priority if n in options][:num_choices]

    def choose_squire_option(self, state, player, options):
        # The generic AI always gains Silver. An engine needs Squire's
        # actions to play its draw terminals, so do not strand them.
        terminals = sum(c.is_action and c.stats.actions == 0 for c in player.hand)
        if terminals > player.actions and "actions" in options:
            return "actions"
        money = player.coins + sum(c.stats.coins for c in player.hand if c.is_treasure)
        if money >= 8 and player.buys == 1 and "buys" in options:
            return "buys"
        if state.supply.get("Silver", 0) > 0 and "silver" in options:
            return "silver"
        return "actions" if "actions" in options else options[0]


def create_sentry_hunting_party_best_found() -> EnhancedStrategy:
    """Frozen winner of the eight-policy finalist tournament."""
    strategy = UnusedKingdomPolicy(
        "sentry_hunting_party",
        targets=[
            ["Vassal", 1],
            ["Candlestick Maker", 1],
            ["Sentry", 5],
            ["Conspirator", 2],
            ["Hunting Party", 1],
        ],
        silver=3,
        gold=2,
        green=12,
        duchy=3,
        opening="Hunting Party",
        minion_redraw=3,
        attack_first=True,
    )
    strategy.name = "Sentry Hunting Party Best Found"
    strategy.description = "Sentry thinning with Vassal, Candlestick Maker and Conspirator; buy Provinces from turn 12 or with four remaining."
    return strategy


def create_minion_courtier_best_found() -> EnhancedStrategy:
    """Frozen winner of the eight-policy finalist tournament."""
    strategy = UnusedKingdomPolicy(
        "minion_courtier",
        targets=[["Baron", 2]],
        opening="Baron",
    )
    strategy.name = "Minion Courtier Best Found"
    strategy.description = "Two Barons support a Gold and Province money deck; prefer Baron in the opening and Duchies at three Provinces remaining."
    return strategy


def create_old_witch_rabble_best_found() -> EnhancedStrategy:
    """Frozen winner of the eight-policy finalist tournament."""
    strategy = UnusedKingdomPolicy(
        "old_witch_rabble",
        targets=[["Warehouse", 1], ["Soothsayer", 2], ["Caravan", 1], ["Spices", 5]],
        silver=99,
        gold=99,
        green=8,
        duchy=2,
        opening="Silver",
        minion_redraw=2,
        attack_first=True,
    )
    strategy.name = "Old Witch Rabble Best Found"
    strategy.description = "Warehouse and Caravan support two Soothsayers and Spices; prefer Silver in the opening and Provinces from turn eight."
    return strategy

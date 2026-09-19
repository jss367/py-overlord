"""Searched policies for a kingdom of ten historically unused cards."""

from collections import Counter

from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule

KINGDOM = (
    "Farming Village",
    "Hunting Grounds",
    "Menagerie",
    "Raze",
    "Apprentice",
    "Woodcutter",
    "Ghost Ship",
    "Cache",
    "Quarry",
    "Bishop",
)
ACTION_ORDER = (
    "Farming Village",
    "Raze",
    "Apprentice",
    "Menagerie",
    "Ghost Ship",
    "Hunting Grounds",
    "Woodcutter",
    "Bishop",
)


class HuntingGroundsPolicy(EnhancedStrategy):
    """Deck targets, adaptive village support and conservative trashing."""

    def __init__(
        self,
        *,
        targets=(),
        opening="Silver",
        silver=99,
        gold=99,
        green=0,
        duchy=3,
        village_ratio=0,
        copper_floor=3,
        bishop_fodder=False,
        draw_first=False,
    ):
        super().__init__()
        self.params = dict(
            targets=[list(t) for t in targets],
            opening=opening,
            silver=silver,
            gold=gold,
            green=green,
            duchy=duchy,
            village_ratio=village_ratio,
            copper_floor=copper_floor,
            bishop_fodder=bishop_fodder,
            draw_first=draw_first,
        )
        self.name = "Hunting Grounds and Ghost Ship"
        self.description = "A searched policy on ten previously unused kingdom piles."
        active = {n for n, cap in targets if cap} | {opening}
        if village_ratio:
            active.add("Farming Village")
        self.action_priority = [PriorityRule(n) for n in ACTION_ORDER if n in active]
        self.gain_priority = [
            PriorityRule(n)
            for n in dict.fromkeys(
                [
                    "Province",
                    "Duchy",
                    "Estate",
                    *[n for n in KINGDOM if n in active],
                    "Gold",
                    "Silver",
                ]
            )
        ]
        self.treasure_priority = [
            PriorityRule(n)
            for n in ("Quarry", "Gold", "Cache", "Silver", "Copper")
            if n in active or n in {"Gold", "Silver", "Copper"}
        ]
        self.trash_priority = [PriorityRule(n) for n in ("Curse", "Estate", "Copper")]

    @staticmethod
    def pick(choices, names):
        return next(
            (c for n in names for c in choices if c is not None and c.name == n), None
        )

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
        terminals = sum(
            counts[n] for n in ("Hunting Grounds", "Ghost Ship", "Woodcutter", "Bishop")
        )
        if (
            p["village_ratio"]
            and counts["Farming Village"] < max(0, terminals - 1) * p["village_ratio"]
        ):
            names.append("Farming Village")
        for name, cap in p["targets"]:
            if counts[name] < cap:
                # Stop rebuying a self-trashed Raze once starting junk is gone.
                if name == "Raze" and not (
                    counts["Estate"] or counts["Copper"] > p["copper_floor"]
                ):
                    continue
                names.append(name)
        if counts["Gold"] < p["gold"]:
            names.append("Gold")
        if counts["Silver"] < p["silver"]:
            names.append("Silver")
        return self.pick(choices, names)

    def junk(self, player, choices):
        names = ["Curse", "Estate"]
        cards = player.all_cards()
        money = sum(c.stats.coins for c in cards if c.is_treasure)
        if (
            sum(c.name == "Copper" for c in cards) > self.params["copper_floor"]
            and money > 5
        ):
            names.append("Copper")
        return self.pick(choices, names)

    def choose_action(self, state, player, choices):
        names = list(ACTION_ORDER)
        if self.params["draw_first"]:
            names.remove("Hunting Grounds")
            names.insert(names.index("Ghost Ship"), "Hunting Grounds")
        # Mandatory trashers must have an acceptable target before being played.
        if self.junk(player, player.hand) is None:
            names.remove("Apprentice")
            if not self.params["bishop_fodder"] or not self.pick(
                player.hand, ["Hunting Grounds", "Gold", "Cache"]
            ):
                names.remove("Bishop")
        return self.pick(choices, names)

    def choose_trash(self, state, player, choices):
        # Bishop also asks opponents to trash. Recover the owner of their cards;
        # GeneticAI's generic trash hook otherwise supplies the active player.
        if None in choices:
            owner = next(
                (
                    p
                    for p in state.players
                    if any(c is h for c in choices if c for h in p.hand)
                ),
                player,
            )
            return self.junk(owner, choices)
        junk = self.junk(player, choices)
        if junk is not None:
            return junk
        if self.params["bishop_fodder"]:
            return self.pick(choices, ["Hunting Grounds", "Cache", "Gold"])
        return min(
            (c for c in choices if c),
            key=lambda c: (c.is_victory, c.cost.coins, c.name),
            default=None,
        )

    def choose_card_to_raze(self, state, player, choices):
        return self.junk(player, choices) or self.pick(choices, ["Raze"])

    def choose_card_to_keep_from_raze(self, state, player, choices):
        action = self.choose_action(state, player, choices)
        return action or max(
            choices, key=lambda c: (c.stats.coins, c.cost.coins), default=None
        )

    def choose_card_to_topdeck_from_hand(self, state, player, choices, reason=None):
        # Keep a draw card plus village when possible; put dead VP and weak
        # treasures back first. All search opponents share this defense.
        counts = Counter(c.name for c in player.hand)

        def value(c):
            if c.name == "Curse" or c.is_victory:
                return 0
            if c.name == "Copper":
                return 1
            if c.name == "Quarry":
                return 2
            if c.name == "Silver":
                return 3
            if c.name in {"Gold", "Cache"}:
                return 5
            if c.name in {"Raze", "Apprentice", "Bishop"}:
                return 2 if not self.junk(player, player.hand) else 6
            if c.name == "Farming Village":
                return 4 if counts[c.name] > 1 else 9
            return 10 if c.name in {"Hunting Grounds", "Ghost Ship", "Menagerie"} else 4

        return min(
            choices, key=lambda c: (value(c), c.cost.coins, c.name), default=None
        )


def create_hunting_grounds_ghost_ship() -> EnhancedStrategy:
    """Frozen tuning winner, independently validated on fresh paired seeds."""
    strategy = HuntingGroundsPolicy(
        targets=[["Raze", 2], ["Ghost Ship", 2], ["Hunting Grounds", 1]],
        opening="Ghost Ship",
        village_ratio=1,
        silver=99,
        gold=2,
        green=12,
        duchy=4,
        copper_floor=2,
        bishop_fodder=True,
        draw_first=False,
    )
    strategy.description = (
        "Raze thinning, two Ghost Ships and one Hunting Grounds with adaptive "
        "Farming Village support; buy Provinces from turn 12 or with four left."
    )
    return strategy

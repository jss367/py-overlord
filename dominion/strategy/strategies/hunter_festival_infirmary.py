"""Hunter/Festival/Infirmary strategy for the Inspiring Supplies board."""

from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


JUNK_CARDS = {"Hovel", "Overgrown Estate", "Estate", "Copper", "Curse"}


def _colonies_left(op: str, amount: int):
    cmp = PriorityRule._OP_MAP[op]
    return lambda state, _player: cmp(state.supply.get("Colony", 0), amount)


class HunterFestivalInfirmaryStrategy(EnhancedStrategy):
    """Exact-cost Hunter/Supplies build with one Festival and Infirmary cleanup."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "Hunter Festival Infirmary"
        self.description = (
            "Hunter/Supplies engine with one Festival, one Infirmary for cleanup, "
            "and conditional Triumph conversion after same-turn gains."
        )
        self.version = "1.0"

        # Mostly documentary: choose_gain below owns the exact-cost buy logic,
        # but these references keep loaders/reports aware of the board pieces.
        self.gain_priority = [
            PriorityRule("Colony"),
            PriorityRule("Province", _colonies_left("<=", 3)),
            PriorityRule("Triumph", PriorityRule.cards_gained_this_turn(">=", 1)),
            PriorityRule("Platinum"),
            PriorityRule("Gold"),
            PriorityRule("Hunter", PriorityRule.max_in_deck("Hunter", 4)),
            PriorityRule("Festival", PriorityRule.max_in_deck("Festival", 1)),
            PriorityRule("Council Room", PriorityRule.max_in_deck("Council Room", 2)),
            PriorityRule("Smithy", PriorityRule.max_in_deck("Smithy", 1)),
            PriorityRule("Infirmary", PriorityRule.max_in_deck("Infirmary", 1)),
            PriorityRule("Supplies", PriorityRule.max_in_deck("Supplies", 5)),
            PriorityRule("Duchy", _colonies_left("<=", 2)),
            PriorityRule("Silver"),
        ]
        self.action_priority = [
            PriorityRule("Festival"),
            PriorityRule("Hunter"),
            PriorityRule("Horse"),
            PriorityRule("Council Room"),
            PriorityRule("Infirmary"),
            PriorityRule("Smithy"),
            PriorityRule("Necropolis"),
            PriorityRule("Mystic"),
            PriorityRule("Vault"),
            PriorityRule("Storeroom"),
            PriorityRule("Change"),
        ]
        self.trash_priority = [
            PriorityRule("Hovel"),
            PriorityRule("Overgrown Estate"),
            PriorityRule("Estate"),
            PriorityRule("Curse"),
            PriorityRule("Copper"),
        ]
        self.treasure_priority = [
            PriorityRule("Platinum"),
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Supplies"),
            PriorityRule("Copper"),
        ]

    @staticmethod
    def _count(player, card_name: str) -> int:
        return player.count_in_deck(card_name)

    def _junk_count(self, player) -> int:
        return sum(self._count(player, card_name) for card_name in JUNK_CARDS)

    def choose_gain(self, state, player, choices):
        cards = {card.name: card for card in choices if card is not None}
        coins = player.coins + player.coin_tokens
        colonies = state.supply.get("Colony", 0)

        if "Colony" in cards:
            return cards["Colony"]
        if colonies <= 3 and "Province" in cards:
            return cards["Province"]

        if (
            player.cards_gained_this_turn >= 1
            and coins >= 5
            and colonies <= 4
            and "Triumph" in cards
        ):
            return cards["Triumph"]

        if "Platinum" in cards:
            return cards["Platinum"]
        if coins >= 6 and "Gold" in cards:
            return cards["Gold"]

        if coins == 5:
            for card_name, limit in (
                ("Hunter", 4),
                ("Festival", 1),
                ("Council Room", 2),
                ("Smithy", 1),
            ):
                if self._count(player, card_name) < limit and card_name in cards:
                    return cards[card_name]

        if coins == 4:
            if self._count(player, "Smithy") < 1 and "Smithy" in cards:
                return cards["Smithy"]
            if (
                self._count(player, "Infirmary") < 1
                and self._junk_count(player) >= 3
                and "Infirmary" in cards
            ):
                return cards["Infirmary"]
            if self._count(player, "Supplies") < 5 and "Supplies" in cards:
                return cards["Supplies"]

        if coins == 3:
            if (
                self._count(player, "Infirmary") < 1
                and self._junk_count(player) >= 3
                and "Infirmary" in cards
            ):
                return cards["Infirmary"]
            if self._count(player, "Supplies") < 5 and "Supplies" in cards:
                return cards["Supplies"]

        if coins <= 2 and self._count(player, "Supplies") < 5 and "Supplies" in cards:
            return cards["Supplies"]
        if colonies <= 2 and "Duchy" in cards:
            return cards["Duchy"]
        if "Silver" in cards:
            return cards["Silver"]
        return None


def create_hunter_festival_infirmary() -> EnhancedStrategy:
    return HunterFestivalInfirmaryStrategy()

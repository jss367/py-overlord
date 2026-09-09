"""Best strategy found for the Bilbao board (``boards/bilbao.txt``).

See ``reports/strategies/bilbao-strategy-guide.html`` for the search and validation.

Chassis: Anvil / Fool's Gold / Feodum money. Three Anvils are bought with
the first $3-$4 hands; every Anvil play discards a Copper to gain a Fool's
Gold (the Rich trait adds a Silver) or, once the deck holds three Silvers, a
Feodum. Fool's Gold is bought ahead of Silver at every $2-$6 hand that does
not buy a Feodum, Gold only at $7, Provinces at $8, Duchies from six
Provinces left, never Estates. Silvers arrive for free with every Fool's
Gold and make each Feodum worth 3-5 VP by the end.

The Anvil policy is hand-written: skip the gain when discarding the Copper
would drop the hand below $8, discard a Copper first, then a lone first
Fool's Gold (worth only $1), then a Silver. The Fool's Gold reaction fires
once per opponent Province (the AI default): Shaman's setup rule returns
that one trashed Fool's Gold to its owner at the start of their next turn.
"""

from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


def _hand_money(player) -> int:
    """Coins this hand can still produce, Fool's Gold bonus included."""
    fg_played = getattr(player, "fools_gold_played", 0)
    total = player.coins
    for card in player.hand:
        if not card.is_treasure:
            continue
        if card.name == "Fool's Gold":
            total += 1 if fg_played == 0 else 4
            fg_played += 1
        else:
            total += card.stats.coins
    return total


def _anvil_discard_value(player, card) -> int:
    """Coins the hand loses by discarding ``card`` to Anvil."""
    if card.name == "Fool's Gold":
        first = getattr(player, "fools_gold_played", 0) == 0 and not any(
            c.name == "Fool's Gold" for c in player.in_play
        )
        only_one = sum(1 for c in player.hand if c.name == "Fool's Gold") == 1
        return 1 if first and only_one else 4
    return card.stats.coins


class BilbaoBestFound(EnhancedStrategy):
    def __init__(self) -> None:
        super().__init__()
        self.name = "Bilbao Best Found"
        self.description = (
            "Three Anvils turn Coppers into Fool's Gold+Silver and Feodums; "
            "Fool's Gold over Silver, Feodum from three Silvers, Duchies from six Provinces left."
        )
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule("Province", PriorityRule.resources("coins", ">=", 8)),
            PriorityRule("Duchy", PriorityRule.provinces_left("<=", 6)),
            PriorityRule(
                "Anvil",
                PriorityRule.and_(
                    PriorityRule.max_in_deck("Anvil", 3),
                    PriorityRule.turn_number("<=", 10),
                ),
            ),
            PriorityRule(
                "Feodum",
                PriorityRule.and_(
                    PriorityRule.has_cards(["Silver"], 3),
                    PriorityRule.max_in_deck("Feodum", 8),
                ),
            ),
            PriorityRule("Gold", PriorityRule.resources("coins", ">=", 7)),
            PriorityRule("Fool's Gold", PriorityRule.max_in_deck("Fool's Gold", 8)),
            PriorityRule("Feodum", PriorityRule.provinces_left("<=", 4)),
            PriorityRule("Silver"),
        ]
        self.action_priority = []
        self.trash_priority = [PriorityRule("Curse")]
        # Anvil first so a Copper is still in hand for its discard.
        self.treasure_priority = [
            PriorityRule("Anvil"),
            PriorityRule("Gold"),
            PriorityRule("Fool's Gold"),
            PriorityRule("Silver"),
            PriorityRule("Copper"),
        ]

    # ---- Anvil policy ----------------------------------------------------

    def choose_anvil_gain(self, state, player, choices):
        """Gain through the ordinary gain list, unless the Treasure that
        would be discarded (Copper, a lone first Fool's Gold, or a Silver)
        costs this hand a Province."""
        treasures = [c for c in player.hand if c.is_treasure]
        discard = self.choose_anvil_treasure_to_discard(state, player, treasures)
        if discard is None:
            return None
        money = _hand_money(player)
        if money >= 8 and money - _anvil_discard_value(player, discard) < 8:
            return None
        return self.choose_gain(state, player, choices)

    def choose_anvil_treasure_to_discard(self, state, player, choices):
        for card in choices:
            if card.name == "Copper":
                return card
        fg_in_hand = [c for c in choices if c.name == "Fool's Gold"]
        if (
            len(fg_in_hand) == 1
            and getattr(player, "fools_gold_played", 0) == 0
            and not any(c.name == "Fool's Gold" for c in player.in_play)
        ):
            return fg_in_hand[0]
        for card in choices:
            if card.name == "Silver":
                return card
        return None

    # Fool's Gold reaction: the AI default already handles Shaman's setup
    # rule (react once per trigger, only when this player acts next).


def create_bilbao_best_found() -> EnhancedStrategy:
    return BilbaoBestFound()

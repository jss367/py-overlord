from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class TorturerEngine(EnhancedStrategy):
    """Engine strategy focused on Torturer, Inn, Snowy Village, and Patrol."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "TorturerEngine"
        self.description = "Hand-tuned Torturer/Inn/Snowy Village engine with Patrol draw"
        self.version = "3.1"

        def terminal_need(me) -> int:
            """Approximate number of terminal actions we want to support."""
            return (
                me.count_in_deck("Torturer")
                + me.count_in_deck("Patrol")
                + me.count_in_deck("Taskmaster")
                + max(0, me.count_in_deck("Inn") - 1)
            )

        def village_capacity(me) -> int:
            """Village effects plus banked villagers from Acting Troupe."""
            return (
                me.count_in_deck("Snowy Village")
                + (2 * me.count_in_deck("Acting Troupe"))
                + (2 * me.count_in_deck("Inn"))
            )

        def need_more_villages(_s, me) -> bool:
            return village_capacity(me) < terminal_need(me)

        def deck_drawing_up(_s, me) -> bool:
            return me.count_in_deck("Patrol") >= 2 or me.count_in_deck("Inn") >= 2

        def torturer_ceiling(_s, me) -> bool:
            # Allow a fourth Torturer only after draw and villages are online
            return me.count_in_deck("Torturer") < 3 or (deck_drawing_up(None, me) and not need_more_villages(None, me))

        def want_second_inn(_s, me) -> bool:
            return me.count_in_deck("Inn") == 1 and me.count_in_deck("Patrol") >= 2

        def want_trail(_s, me) -> bool:
            # Prioritize Trail if we expect hand-size attacks or already have curses
            return me.count_in_deck("Trail") < max(2, me.count_in_deck("Curse"))

        def enough_payload(_s, me) -> bool:
            return me.count_in_deck("Gold") + me.count_in_deck("Emporium") >= 2

        # Gain priorities
        self.gain_priority = [
            # Provinces once the deck can reliably hit 8 or the game is ending
            PriorityRule(
                "Province",
                PriorityRule.or_(
                    PriorityRule.resources("coins", ">=", 8),
                    PriorityRule.provinces_left("<=", 4),
                ),
            ),
            # Engine cards - early priorities
            PriorityRule(
                "Torturer",
                PriorityRule.and_(
                    PriorityRule.resources("coins", ">=", 5),
                    torturer_ceiling,
                ),
            ),
            # Smooth early economy: pick up a Silver before the first $5 cost
            PriorityRule(
                "Silver",
                PriorityRule.and_(
                    PriorityRule.resources("coins", ">=", 3),
                    lambda _s, me: me.count_in_deck("Silver") == 0,
                    lambda _s, me: me.count_in_deck("Torturer") == 0,
                ),
            ),
            PriorityRule(
                "Inn",
                PriorityRule.and_(
                    PriorityRule.resources("coins", ">=", 5),
                    lambda _s, me: me.count_in_deck("Inn") == 0,
                ),
            ),
            PriorityRule(
                "Patrol",
                PriorityRule.and_(
                    PriorityRule.resources("coins", ">=", 5),
                    lambda _s, me: me.count_in_deck("Patrol") < 2,
                ),
            ),
            # Bank villagers early to avoid terminal collisions
            PriorityRule(
                "Acting Troupe",
                PriorityRule.and_(
                    PriorityRule.resources("coins", ">=", 3),
                    lambda _s, me: me.count_in_deck("Acting Troupe") < 1,
                ),
            ),
            PriorityRule(
                "Snowy Village",
                PriorityRule.and_(
                    PriorityRule.resources("coins", ">=", 4),
                    need_more_villages,
                ),
            ),
            PriorityRule(
                "Inn",
                PriorityRule.and_(
                    PriorityRule.resources("coins", ">=", 5),
                    want_second_inn,
                ),
            ),
            PriorityRule(
                "Patrol",
                PriorityRule.and_(
                    PriorityRule.resources("coins", ">=", 5),
                    lambda _s, me: me.count_in_deck("Patrol") < 3,
                ),
            ),
            # Trail for defense against Torturer attacks
            PriorityRule(
                "Trail",
                PriorityRule.and_(
                    PriorityRule.resources("coins", ">=", 4),
                    want_trail,
                ),
            ),
            # Taskmaster to play multiple Torturers - ensure support first
            PriorityRule(
                "Taskmaster",
                PriorityRule.and_(
                    PriorityRule.resources("coins", ">=", 5),
                    lambda _s, me: me.count_in_deck("Torturer") >= 1,
                    lambda _s, me: not need_more_villages(None, me),
                    lambda _s, me: me.count_in_deck("Taskmaster") < 1,
                ),
            ),
            PriorityRule(
                "Taskmaster",
                PriorityRule.and_(
                    PriorityRule.resources("coins", ">=", 5),
                    lambda _s, me: me.count_in_deck("Torturer") >= 2,
                    lambda _s, me: not need_more_villages(None, me),
                    lambda _s, me: me.count_in_deck("Taskmaster") < 2,
                ),
            ),
            # Emporium for bonus points when we have long action chains
            PriorityRule(
                "Emporium",
                PriorityRule.and_(
                    PriorityRule.resources("coins", ">=", 5),
                    lambda s, me: me.actions_this_turn >= 4
                    or (me.count_in_deck("Patrician") >= 2 and not need_more_villages(s, me)),
                ),
            ),
            # Additional payload once the engine is drawing
            PriorityRule(
                "Gold",
                PriorityRule.and_(
                    PriorityRule.resources("coins", ">=", 6),
                    deck_drawing_up,
                ),
            ),
            # Continue adding Torturers when the deck can support them
            PriorityRule(
                "Torturer",
                PriorityRule.and_(
                    PriorityRule.resources("coins", ">=", 5),
                    lambda _s, me: not need_more_villages(None, me),
                    lambda _s, me: deck_drawing_up(None, me),
                ),
            ),
            # Greening & pile control
            PriorityRule(
                "Duchy",
                PriorityRule.or_(
                    PriorityRule.provinces_left("<=", 6),
                    lambda s, _me: s.supply.get("Patrician", 0) <= 2,
                    lambda s, _me: s.supply.get("Snowy Village", 0) <= 2,
                ),
            ),
            PriorityRule(
                "Estate",
                PriorityRule.or_(
                    PriorityRule.provinces_left("<=", 3),
                    PriorityRule.and_(
                        lambda s, _me: (
                            (1 if s.supply.get("Estate", 99) <= 1 else 0)
                            + (1 if s.supply.get("Patrician", 99) <= 1 else 0)
                            + (1 if s.supply.get("Snowy Village", 99) <= 1 else 0)
                            + (1 if s.supply.get("Trail", 99) <= 1 else 0)
                        )
                        >= 2,
                        lambda _s, _me: True,
                    ),
                ),
            ),
            # Pick up extra Trail for Curse conversion in drawn-out games
            PriorityRule(
                "Trail",
                PriorityRule.and_(
                    PriorityRule.resources("coins", ">=", 4),
                    lambda _s, me: me.count_in_deck("Curse") > 0,
                ),
            ),
            # Ensure we have enough treasure when the engine is thin
            PriorityRule(
                "Silver",
                PriorityRule.and_(
                    PriorityRule.resources("coins", ">=", 3),
                    lambda _s, me: deck_drawing_up(None, me),
                    lambda _s, me: not enough_payload(None, me),
                ),
            ),
        ]

        # Action priorities - village effects first, then draw, payload, attacks
        self.action_priority = [
            PriorityRule("Patrician"),  # +1 card +1 action
            PriorityRule("Acting Troupe"),  # Bank villagers before doubling
            PriorityRule("Inn"),  # +2 cards +2 actions
            PriorityRule("Snowy Village"),
            PriorityRule("Taskmaster"),  # Play other actions multiple times
            PriorityRule("Patrol"),  # +3 cards
            PriorityRule("Emporium"),  # Treasure/Action
            PriorityRule("Torturer"),  # Attack last
        ]

        # Trash priorities - get rid of junk
        self.trash_priority = [
            PriorityRule("Curse"),
            PriorityRule("Overgrown Estate"),
            PriorityRule("Hovel"),
            PriorityRule("Necropolis"),
            PriorityRule("Estate"),
            PriorityRule("Copper"),
        ]

        # Treasure play order
        self.treasure_priority = [
            PriorityRule("Gold"),
            PriorityRule("Silver"),
            PriorityRule("Copper"),
        ]

        # Special reaction priorities
        self.reaction_priority = [
            PriorityRule("Trail"),  # Discard Trail when opponent plays attack
        ]


def create_torturer_engine() -> EnhancedStrategy:
    return TorturerEngine()

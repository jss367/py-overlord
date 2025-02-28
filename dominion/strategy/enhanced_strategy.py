from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


def create_big_money_strategy() -> EnhancedStrategy:
    """Classic Big Money strategy focusing on treasure acquisition."""
    strategy = EnhancedStrategy()
    strategy.name = "BigMoney"

    # Gain priorities
    strategy.gain_priority = [
        # Buy Province if we can afford it
        PriorityRule("Province", PriorityRule.can_afford(8)),
        # Buy Duchy late game
        PriorityRule("Duchy", PriorityRule.and_(PriorityRule.provinces_left("<=", 4), PriorityRule.can_afford(5))),
        # Buy Gold if we can afford it
        PriorityRule("Gold", PriorityRule.can_afford(6)),
        # Buy Silver if we can afford it and it's not too late
        PriorityRule("Silver", PriorityRule.and_(PriorityRule.can_afford(3), PriorityRule.provinces_left(">", 2))),
    ]

    # Simple treasure playing order
    strategy.treasure_priority = [
        PriorityRule("Gold"),
        PriorityRule("Silver"),
        PriorityRule("Copper"),
    ]

    return strategy


def create_chapel_witch_strategy() -> EnhancedStrategy:
    """Chapel/Witch engine strategy."""
    strategy = EnhancedStrategy()
    strategy.name = "ChapelWitch"

    # Action priorities
    strategy.action_priority = [
        # Chapel early for deck thinning
        PriorityRule(
            "Chapel",
            PriorityRule.and_(
                PriorityRule.turn_number("<=", 6),
                PriorityRule.or_(PriorityRule.has_cards(["Copper"], 1), PriorityRule.has_cards(["Estate"], 1)),
            ),
        ),
        # Village for actions
        PriorityRule("Village", PriorityRule.resources("actions", "<", 2)),
        # Witch for attacks
        PriorityRule(
            "Witch", PriorityRule.and_(PriorityRule.turn_number(">=", 3), PriorityRule.resources("actions", ">=", 1))
        ),
        # Laboratory for draw
        PriorityRule("Laboratory", PriorityRule.always_true),
    ]

    # Gain priorities
    strategy.gain_priority = [
        # Victory cards
        PriorityRule("Province", PriorityRule.can_afford(8)),
        PriorityRule("Duchy", PriorityRule.and_(PriorityRule.provinces_left("<=", 5), PriorityRule.can_afford(5))),
        # Engine pieces
        PriorityRule(
            "Witch",
            PriorityRule.and_(
                PriorityRule.turn_number("<", 15), PriorityRule.has_cards(["Witch"], 0), PriorityRule.can_afford(5)
            ),
        ),
        PriorityRule(
            "Chapel",
            PriorityRule.and_(
                PriorityRule.turn_number("<=", 4), PriorityRule.has_cards(["Chapel"], 0), PriorityRule.can_afford(2)
            ),
        ),
        PriorityRule(
            "Laboratory",
            PriorityRule.and_(
                PriorityRule.turn_number("<", 12),
                PriorityRule.resources("actions", ">=", 1),
                PriorityRule.can_afford(5),
            ),
        ),
        PriorityRule(
            "Village",
            PriorityRule.and_(
                PriorityRule.turn_number("<", 12),
                PriorityRule.has_cards(["Village", "Laboratory", "Witch"], 2),
                PriorityRule.can_afford(3),
            ),
        ),
        # Treasure
        PriorityRule("Gold", PriorityRule.can_afford(6)),
        PriorityRule("Silver", PriorityRule.and_(PriorityRule.turn_number("<", 10), PriorityRule.can_afford(3))),
    ]

    # Treasure priorities
    strategy.treasure_priority = [
        PriorityRule("Gold"),
        PriorityRule("Silver"),
        PriorityRule("Copper"),
    ]

    # Trash priorities
    strategy.trash_priority = [
        PriorityRule("Curse"),
        PriorityRule("Estate", PriorityRule.provinces_left(">", 4)),
        PriorityRule(
            "Copper",
            PriorityRule.and_(PriorityRule.has_cards(["Silver", "Gold"], 3), PriorityRule.turn_number("<", 10)),
        ),
    ]

    return strategy


def create_village_smithy_lab_strategy() -> EnhancedStrategy:
    """Village/Smithy/Laboratory engine strategy."""
    strategy = EnhancedStrategy()
    strategy.name = "VillageSmithyLab"

    # Action priorities
    strategy.action_priority = [
        # Village first if low on actions
        PriorityRule("Village", PriorityRule.resources("actions", "<", 2)),
        # Laboratory for efficient draw
        PriorityRule("Laboratory", PriorityRule.resources("actions", ">=", 1)),
        # Smithy for draw
        PriorityRule("Smithy", PriorityRule.resources("actions", ">=", 1)),
    ]

    # Gain priorities
    strategy.gain_priority = [
        # Victory cards
        PriorityRule("Province", PriorityRule.can_afford(8)),
        PriorityRule("Duchy", PriorityRule.and_(PriorityRule.provinces_left("<=", 4), PriorityRule.can_afford(5))),
        # Engine pieces
        PriorityRule("Laboratory", PriorityRule.and_(PriorityRule.turn_number("<", 15), PriorityRule.can_afford(5))),
        PriorityRule("Village", PriorityRule.and_(PriorityRule.turn_number("<", 12), PriorityRule.can_afford(3))),
        PriorityRule("Smithy", PriorityRule.and_(PriorityRule.turn_number("<", 12), PriorityRule.can_afford(4))),
        # Treasure
        PriorityRule("Gold", PriorityRule.can_afford(6)),
        PriorityRule("Silver", PriorityRule.and_(PriorityRule.turn_number("<", 8), PriorityRule.can_afford(3))),
    ]

    # Treasure priorities
    strategy.treasure_priority = [
        PriorityRule("Gold"),
        PriorityRule("Silver"),
        PriorityRule("Copper"),
    ]

    return strategy

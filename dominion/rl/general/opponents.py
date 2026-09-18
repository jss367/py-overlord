"""Named baselines and a board-aware teacher used only during training."""

from dominion.ai.genetic_ai import GeneticAI
from dominion.analysis.engine_archetypes import build_engine_seeds
from dominion.boards.loader import BoardConfig
from dominion.cards.registry import get_card
from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule as Rule
from dominion.strategy.strategies.big_money import create_big_money
from dominion.rl.general.encoding import validate_kingdom

BASELINES = ("big_money", "draw_money", "engine")


def teacher_strategy(kingdom):
    """A conservative draw/money teacher with optional Chapel and Witch.

    This is a training teacher and a separately reported baseline, never a
    fallback for the learned agent's choices.
    """
    validate_kingdom(kingdom)
    strategy = EnhancedStrategy()
    strategy.name = "Draw and money teacher"
    strategy.gain_priority = [
        Rule("Province"), Rule("Duchy", Rule.provinces_left("<=", 3)),
        Rule("Estate", Rule.provinces_left("<=", 1)),
        Rule("Chapel", Rule.and_(Rule.turn_number("<=", 2), Rule.max_in_deck("Chapel", 1))),
        Rule("Witch", Rule.and_(lambda s, p: s.supply.get("Curse", 0) > 0,
                               Rule.max_in_deck("Witch", 2))),
    ]
    draw = next((n for n in ("Smithy", "Council Room", "Moat", "Adventurer") if n in kingdom), None)
    if draw:
        strategy.gain_priority.append(Rule(draw, lambda s, p, n=draw:
            p.count_in_deck(n) < (2 if len(p.all_cards()) >= 20 else 1)
            and p.count_in_deck("Witch") == 0))
    strategy.gain_priority.extend([
        Rule("Laboratory", lambda s, p: p.count_in_deck("Laboratory") < 5
             and p.count_in_deck("Gold") >= 1),
        Rule("Gold"),
        Rule("Laboratory", Rule.max_in_deck("Laboratory", 2)),
        Rule("Market", Rule.max_in_deck("Market", 2)),
        Rule("Silver"),
        Rule("Moat", lambda s, p: "Witch" in s.supply and p.count_in_deck("Moat") < 1),
    ])
    actions = sorted((get_card(n) for n in kingdom if get_card(n).is_action),
                     key=lambda c: (c.stats.actions == 0, -c.stats.actions, -c.stats.cards, c.name))
    strategy.action_priority = [Rule(c.name) for c in actions if c.name != "Chapel"]
    strategy.action_priority.insert(0, Rule("Chapel", lambda s, p:
        any(c.name == "Curse" or (c.name == "Estate" and s.supply.get("Province", 0) > 3)
            or (c.name == "Copper" and p.count_in_deck("Silver") + p.count_in_deck("Gold") >= 3)
            for c in p.hand)))
    strategy.trash_priority = [
        Rule("Curse"), Rule("Estate", Rule.provinces_left(">", 3)),
        Rule("Copper", lambda s, p: p.count_in_deck("Silver") + p.count_in_deck("Gold") >= 3),
        Rule("Chapel", lambda s, p: p.count_in_deck("Chapel") > 1),
    ]
    strategy.treasure_priority = [Rule(n) for n in ("Gold", "Farm", "Silver", "Copper")]
    return strategy


def make_opponent(name, kingdom):
    if name == "big_money":
        strategy = create_big_money()
    elif name == "draw_money":
        strategy = teacher_strategy(kingdom)
    elif name == "engine":
        seeds = build_engine_seeds(BoardConfig(list(kingdom)), max_engines=1)
        strategy = seeds[0][1] if seeds else teacher_strategy(kingdom)
    else:
        raise ValueError(f"Unknown baseline: {name}")
    return GeneticAI(strategy)

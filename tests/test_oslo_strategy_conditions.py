from generated_strategies.oslo_workers_village_magnate_engine import (
    OsloWorkersVillageMagnateRefinedEngine,
)
from dominion.strategy.enhanced_strategy import PriorityRule


def test_refined_engine_gain_conditions_have_serializable_sources():
    strategy = OsloWorkersVillageMagnateRefinedEngine()
    rules = {
        rule.card_name: rule
        for rule in strategy.gain_priority
        if rule.card_name in {"Province", "King's Court"}
    }

    for rule in rules.values():
        source = rule.condition._source
        recreated = eval(source, {"PriorityRule": PriorityRule})

        assert callable(recreated)

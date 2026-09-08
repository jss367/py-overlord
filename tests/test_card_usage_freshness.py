import re

from dominion.reporting.card_usage import normalize_card_usage_for_comparison, render_card_usage
from dominion.reporting.strategy_pages import collect_rendered_strategies


def test_freshness_comparison_ignores_only_tournament_rank_fields():
    items = collect_rendered_strategies(names=["Big Money"])
    clean = render_card_usage(items)
    ranked = render_card_usage(items, {"Big Money": {"win_rate": 100}}, context_label="a saved tournament")
    normalize = normalize_card_usage_for_comparison
    assert normalize(clean) == normalize(ranked)
    # Even an unused card's removal must be detected, as must count or style changes.
    missing_card = re.sub(r'<tr data-basic="false"><td data-sort="Advisor">.*?</tr>', '', ranked)
    assert missing_card != ranked
    assert normalize(clean) != normalize(missing_card)
    assert normalize(clean) != normalize(ranked.replace('<strong>1</strong>', '<strong>2</strong>'))
    assert normalize(clean) != normalize(ranked.replace('min-width: 880px', 'min-width: 900px'))

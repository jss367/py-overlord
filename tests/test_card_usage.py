from html import escape
import re

from dominion.reporting.card_usage import collect_card_usage, render_card_usage
from dominion.reporting.html_report import generate_leaderboard_html
from dominion.reporting.strategy_pages import RenderedStrategy, collect_rendered_strategies
from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule, WayRule


def _strategy(name, cards):
    strategy = EnhancedStrategy()
    strategy.gain_priority = [PriorityRule(card) for card in cards]
    return RenderedStrategy(name, name.lower(), strategy, "example.py", "create_example", {})


def test_usage_deduplicates_cards_aliases_and_strategy_entries():
    item = _strategy("Example", ["Council room", "Council Room", "Village", "Village", "Silver", "Treasure", "Invest"])
    item.strategy.action_priority = [PriorityRule("Village")]
    item.strategy.way_policy = [WayRule(card_name="Smithy", way_name="Way of the Ox")]
    rows = {row.name: row for row in collect_card_usage([item, item])}

    assert len(rows["Council Room"].strategies) == 1
    assert len(rows["Village"].strategies) == 1
    assert len(rows["Silver"].strategies) == 1
    assert len(rows["Smithy"].strategies) == 1
    assert rows["Witch"].strategies == ()
    assert "Invest" not in rows
    assert "Treasure" not in rows
    assert rows["Village"].median_rank is None


def test_usage_median_matches_leaderboard_order_and_excludes_unranked():
    strategies = [
        _strategy("Alpha", ["Village", "Smithy"]),
        _strategy("Beta", ["Village"]),
        _strategy("Gamma", ["Village"]),
        _strategy("Unranked", ["Village"]),
    ]
    results = {
        "Gamma": {"win_rate": 50, "wins": 2, "losses": 2},
        "Beta": {"win_rate": 50, "wins": 2, "losses": 1},
        "Alpha": {"win_rate": 50, "wins": 2, "losses": 1},
        "Unknown strategy": {"win_rate": 100},
    }
    rows = {row.name: row for row in collect_card_usage(strategies, results)}
    assert rows["Village"].ranks == (2, 3, 4)
    assert rows["Village"].median_rank == 3
    assert len(rows["Village"].strategies) == 4
    assert rows["Smithy"].median_rank == 2
    assert rows["Witch"].median_rank is None

    strategies[2].strategy.gain_priority = []
    rows = {row.name: row for row in collect_card_usage(strategies, results)}
    assert rows["Village"].median_rank == 2.5


def test_usage_resolves_result_strategy_aliases():
    strategies = collect_rendered_strategies(names=["Big Money"])
    rows = {row.name: row for row in collect_card_usage(strategies, {"BigMoney": {"win_rate": 100}})}
    assert rows["Gold"].median_rank == 1


def test_usage_empty_catalog_and_escaped_content():
    html = render_card_usage([])
    assert "No tournament results yet" in html
    assert 'data-sort="0.0">0.0%' in html or 'data-sort="0">0.0%' in html
    assert "nan" not in html.lower()
    item = _strategy("<Example>", ["Village"])
    html = render_card_usage([item], {"<Example>": {"win_rate": 100}}, context_label="<board>")
    assert "&lt;Example&gt;" in html
    assert "&lt;board&gt;" in html
    assert "<Example>" not in html


def test_usage_expansions_follow_printed_sets_including_misfiled_cards():
    html = render_card_usage([])
    expected = {
        "Village": "Base", "Copper": "Base", "Province": "Base",
        "Colony": "Prosperity", "Potion": "Alchemy", "Hovel": "Dark Ages",
        "Advisor": "Cornucopia & Guilds", "Joust": "Cornucopia & Guilds",
        "Sauna": "Promo", "Astrolabe": "Seaside", "Collection": "Prosperity",
        "Fisherman": "Menagerie", "Snowy Village": "Menagerie",
        "Mill": "Intrigue", "Trading Post": "Intrigue", "Pilgrim": "Plunder",
        "Taskmaster": "Plunder", "Wealthy Village": "Plunder",
        "Tea House": "Rising Sun", "Plunder": "Empires",
    }
    for name, expansion in expected.items():
        assert f'data-expansion="{escape(expansion)}"><td data-sort="{name}">' in html
        assert f'<option value="{escape(expansion)}">{escape(expansion)}</option>' in html
    assert '<label for="card-expansion">Expansion</label>' in html
    assert '<option value="">All expansions</option>' in html


def test_usage_marks_retired_cards_but_keeps_retained_and_renamed_cards():
    html = render_card_usage([])
    retired = dict(re.findall(
        r'data-removed-second-edition="true" data-expansion="([^"]*)"><td data-sort="([^"]*)">',
        html,
    ))
    assert set(retired) == {
        "Base", "Intrigue", "Seaside", "Prosperity", "Hinterlands", "Cornucopia &amp; Guilds",
    }
    retired_names = set(re.findall(
        r'data-removed-second-edition="true"[^>]*><td data-sort="([^"]*)">', html,
    ))
    assert len(retired_names) == 51
    assert {"Adventurer", "Scout", "Sea Hag", "Goons", "Cache", "Doctor", "Tournament", "Princess"} <= retired_names
    assert not {"Farm", "Fairgrounds", "Joust", "Coronet", "Village", "Colony"} & retired_names


def test_tournament_writes_linked_usage_companion(tmp_path):
    output = tmp_path / "sample-tournament.html"
    generate_leaderboard_html({"Chapel Witch": {"win_rate": 100}}, output, context_label="the sample board")
    companion = tmp_path / "sample-tournament-card-strategy-usage.html"
    assert companion.exists()
    assert 'href="sample-tournament-card-strategy-usage.html"' in output.read_text()
    html = companion.read_text()
    assert 'href="sample-tournament.html"' in html
    assert "the sample board" in html
    assert 'data-sort="1">1</td>' in html
    assert "No tournament results yet" not in html


def test_tournament_with_unregistered_entrants_omits_usage_companion(tmp_path):
    output = tmp_path / "evolution-tournament.html"
    results = {
        "Big Money": {"win_rate": 20},
        "Evolved Big Money": {"win_rate": 80},
        "Trick Smithy": {"win_rate": 60},
        "Reuse Previous Champion": {"win_rate": 40},
    }
    generate_leaderboard_html(results, output)

    html = output.read_text()
    for name in results:
        assert name in html
    assert "Card strategy usage" not in html
    assert not (tmp_path / "evolution-tournament-card-strategy-usage.html").exists()


def test_tournament_with_registered_aliases_still_writes_usage(tmp_path):
    output = tmp_path / "leaderboard.html"
    generate_leaderboard_html({"BigMoney": {"win_rate": 100}}, output)

    assert 'href="card-strategy-usage.html"' in output.read_text()
    html = (tmp_path / "card-strategy-usage.html").read_text()
    assert 'data-sort="1">1</td>' in html


def test_tournament_generated_filename_has_usage_and_correct_rank(tmp_path):
    output = tmp_path / "generated-tournament.html"
    results = {"strategy_20260212_094841": {"win_rate": 100}}
    generate_leaderboard_html(results, output)
    assert "Card strategy usage" in output.read_text()
    companion = tmp_path / "generated-tournament-card-strategy-usage.html"
    assert companion.exists()
    items = collect_rendered_strategies(names=["strategy_20260212_094841"])
    rows = collect_card_usage(items, results)
    assert all(row.median_rank == 1 for row in rows if row.strategies)

from dominion.reporting.strategy_links import strategy_page_href, strategy_slug
from dominion.reporting.strategy_pages import (
    render_strategy_leaderboard,
    render_strategy_pages,
)
from dominion.reporting.html_report import (
    _strategy_report_href,
    generate_leaderboard_html,
)


def test_strategy_slug_is_stable_for_display_names():
    assert strategy_slug("Big Money Smithy") == "big-money-smithy"
    assert strategy_page_href("Big Money Smithy") == "strategies/big-money-smithy.html"


def test_strategy_report_href_resolves_aliases_to_rendered_pages():
    assert (
        _strategy_report_href("BigMoney", prefix="strategies")
        == "strategies/big-money.html"
    )
    assert (
        _strategy_report_href("ChapelWitch", prefix="strategies")
        == "strategies/chapel-witch.html"
    )
    assert (
        _strategy_report_href("strategy_20260212_094841", prefix="strategies") is None
    )


def test_leaderboard_html_does_not_link_unresolved_strategy_names(tmp_path):
    output = tmp_path / "leaderboard.html"
    generate_leaderboard_html(
        {
            "Big Money": {
                "wins": 1,
                "losses": 0,
                "win_rate": 100.0,
                "description": "",
                "cards": [],
            },
            "strategy_20260212_094841": {
                "wins": 0,
                "losses": 1,
                "win_rate": 0.0,
                "description": "",
                "cards": [],
            },
        },
        output,
    )

    html = output.read_text(encoding="utf-8")
    assert "big-money.html" in html
    assert "strategy_20260212_094841.html" not in html
    assert "<td>strategy_20260212_094841</td>" in html


def test_strategy_leaderboard_ranks_results_and_links_registered_strategies():
    html = render_strategy_leaderboard(
        {
            "Big Money": {
                "wins": 7,
                "losses": 3,
                "win_rate": 70.0,
                "description": "Simple treasure strategy.",
                "cards": ["Gold", "Province"],
            },
            "Chapel Witch": {
                "wins": 3,
                "losses": 7,
                "win_rate": 30.0,
                "description": "Trash, then attack.",
                "cards": ["Chapel", "Witch"],
            },
        }
    )

    assert "Strategy Leaderboard" in html
    assert 'class="podium-card podium-rank-1"' in html
    assert html.index("Big Money") < html.index("Chapel Witch")
    assert 'href="big-money.html"' in html
    assert "70.0%" in html
    assert 'class="card-chip type-treasure card-gold"' in html


def test_strategy_leaderboard_explains_how_to_generate_results():
    html = render_strategy_leaderboard({})

    assert "No tournament results yet" in html
    assert "python compare_all_strategies.py" in html


def test_render_strategy_pages_writes_index_and_strategy_page(tmp_path):
    written = render_strategy_pages(tmp_path, names=["Big Money"])

    paths = {path.name for path in written}
    assert paths == {
        "index.html",
        "big-money.html",
        "cursed-band-biding-time-strategy-guide.html",
    }

    index = (tmp_path / "index.html").read_text(encoding="utf-8")
    page = (tmp_path / "big-money.html").read_text(encoding="utf-8")
    guide = (tmp_path / "cursed-band-biding-time-strategy-guide.html").read_text(
        encoding="utf-8"
    )

    assert "Strategy Index" in index
    assert 'href="big-money.html"' in index
    assert 'href="cursed-band-biding-time-strategy-guide.html"' in index
    assert "Gain Priority" in page
    assert "Province" in page
    assert "dominion/strategy/strategies/big_money.py" in page
    assert "<title>Cursed Band and Biding Time Strategy Guide</title>" in guide
    assert 'class="card-chip type-victory"' in page
    assert 'class="card-chip type-treasure card-gold"' in page
    assert "Implementation details and referenced components" in page
    assert 'class="priority-table"' in page

    assert 'class="catalog-grid"' in index
    assert 'class="strategy-card strategy-row"' in index
    assert "Curated guide" in index


def test_render_strategy_pages_resolves_alias_names(tmp_path):
    written = render_strategy_pages(tmp_path, names=["BigMoney"])

    paths = {path.name for path in written}
    assert paths == {
        "index.html",
        "big-money.html",
        "cursed-band-biding-time-strategy-guide.html",
    }

    page = (tmp_path / "big-money.html").read_text(encoding="utf-8")
    assert "Big Money" in page
    assert "dominion/strategy/strategies/big_money.py" in page


def test_strategy_pages_distinguish_named_treasures_from_treasure_cards(tmp_path):
    render_strategy_pages(
        tmp_path,
        names=["Oslo Workers Village Magnate Starting Strategy"],
    )

    page = (
        tmp_path / "oslo-workers-village-magnate-starting-strategy.html"
    ).read_text(encoding="utf-8")

    assert '--treasure: #eadca9;' in page
    assert 'class="card-chip type-treasure card-platinum"' in page
    assert 'class="card-chip type-treasure card-gold"' in page
    assert 'class="card-chip type-treasure card-silver"' in page
    assert 'class="card-chip type-treasure card-copper"' in page
    assert 'class="card-chip type-treasure" aria-label="Hoard' in page
    assert '.card-chip.card-platinum {' in page
    assert 'background: #f3efe7;' in page


def test_render_strategy_pages_overwrites_stale_curated_guide(tmp_path):
    guide = tmp_path / "cursed-band-biding-time-strategy-guide.html"
    guide.write_text("stale guide", encoding="utf-8")
    written = render_strategy_pages(tmp_path, names=["Big Money"])

    assert "<title>Cursed Band and Biding Time Strategy Guide</title>" in guide.read_text(
        encoding="utf-8"
    )
    assert guide in written
    index = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert 'href="cursed-band-biding-time-strategy-guide.html"' in index
    assert "Cursed Band and Biding Time Strategy Guide" in index


def test_strategy_page_shows_readable_conditions_and_preserves_source(tmp_path):
    render_strategy_pages(tmp_path, names=["Hyderabad Best Found"])

    page = (tmp_path / "hyderabad-best-found.html").read_text(encoding="utf-8")

    assert "Provinces remaining: at most" in page
    assert "PriorityRule.provinces_left" in page
    assert 'class="condition-detail"' in page


def test_strategy_page_recovers_plain_english_from_untagged_lambdas(tmp_path):
    render_strategy_pages(tmp_path, names=["Chapel Witch"])

    page = (tmp_path / "chapel-witch.html").read_text(encoding="utf-8")

    assert "You own no Witch" in page
    assert "Turn number: at most 2 and You own no Chapel" in page
    assert "Special strategy rule" not in page
    assert "custom condition" not in page


def test_strategy_page_shows_custom_function_source_and_configured_values(tmp_path):
    render_strategy_pages(
        tmp_path,
        names=["Oslo Workers Village Magnate Multi Colony Engine"],
    )

    page = (
        tmp_path / "oslo-workers-village-magnate-multi-colony-engine.html"
    ).read_text(encoding="utf-8")

    assert "Multi colony greening gate (fallback turn: 20; min colonies: 4)" in page
    assert "Hold copper for anvil (magnate limit: 7; village limit: 7)" in page
    assert "Configured values: fallback_turn = 20, min_colonies = 4" in page
    assert "player.count_in_deck(&quot;Colony&quot;) &gt; 0" in page
    assert "Special strategy rule" not in page
    assert "custom condition" not in page

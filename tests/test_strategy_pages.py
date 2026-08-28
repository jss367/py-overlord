from dominion.reporting.strategy_links import strategy_page_href, strategy_slug
from dominion.reporting.strategy_pages import render_strategy_pages
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


def test_render_strategy_pages_writes_index_and_strategy_page(tmp_path):
    written = render_strategy_pages(tmp_path, names=["Big Money"])

    paths = {path.name for path in written}
    assert paths == {"index.html", "big-money.html"}

    index = (tmp_path / "index.html").read_text(encoding="utf-8")
    page = (tmp_path / "big-money.html").read_text(encoding="utf-8")

    assert "Strategy Index" in index
    assert 'href="big-money.html"' in index
    assert "Gain Priority" in page
    assert "Province" in page
    assert "dominion/strategy/strategies/big_money.py" in page
    assert 'class="card-chip type-victory"' in page
    assert 'class="card-chip type-treasure card-gold"' in page
    assert "Implementation details and referenced components" in page
    assert 'class="priority-table"' in page

    assert 'class="catalog-grid"' in index
    assert 'class="strategy-card strategy-row"' in index


def test_render_strategy_pages_resolves_alias_names(tmp_path):
    written = render_strategy_pages(tmp_path, names=["BigMoney"])

    paths = {path.name for path in written}
    assert paths == {"index.html", "big-money.html"}

    page = (tmp_path / "big-money.html").read_text(encoding="utf-8")
    assert "Big Money" in page
    assert "dominion/strategy/strategies/big_money.py" in page


def test_strategy_page_shows_readable_conditions_and_preserves_source(tmp_path):
    render_strategy_pages(tmp_path, names=["Hyderabad Best Found"])

    page = (tmp_path / "hyderabad-best-found.html").read_text(encoding="utf-8")

    assert "Provinces remaining: at most" in page
    assert "PriorityRule.provinces_left" in page
    assert 'class="condition-detail"' in page

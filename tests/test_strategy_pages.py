from dominion.reporting.strategy_links import strategy_page_href, strategy_slug
from dominion.reporting.strategy_pages import render_strategy_pages
from dominion.reporting.html_report import _strategy_report_href, generate_leaderboard_html


def test_strategy_slug_is_stable_for_display_names():
    assert strategy_slug("Big Money Smithy") == "big-money-smithy"
    assert strategy_page_href("Big Money Smithy") == "strategies/big-money-smithy.html"


def test_strategy_report_href_resolves_aliases_to_rendered_pages():
    assert _strategy_report_href("BigMoney", prefix="strategies") == "strategies/big-money.html"
    assert _strategy_report_href("ChapelWitch", prefix="strategies") == "strategies/chapel-witch.html"
    assert _strategy_report_href("strategy_20260212_094841", prefix="strategies") is None


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

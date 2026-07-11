from dominion.reporting.strategy_links import strategy_page_href, strategy_slug
from dominion.reporting.strategy_pages import render_strategy_pages
from dominion.reporting.html_report import _strategy_report_href


def test_strategy_slug_is_stable_for_display_names():
    assert strategy_slug("Big Money Smithy") == "big-money-smithy"
    assert strategy_page_href("Big Money Smithy") == "strategies/big-money-smithy.html"


def test_strategy_report_href_resolves_aliases_to_rendered_pages():
    assert _strategy_report_href("BigMoney", prefix="strategies") == "strategies/big-money.html"
    assert _strategy_report_href("ChapelWitch", prefix="strategies") == "strategies/chapel-witch.html"


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


def test_render_strategy_pages_resolves_alias_names(tmp_path):
    written = render_strategy_pages(tmp_path, names=["BigMoney"])

    paths = {path.name for path in written}
    assert paths == {"index.html", "big-money.html"}

    page = (tmp_path / "big-money.html").read_text(encoding="utf-8")
    assert "Big Money" in page
    assert "dominion/strategy/strategies/big_money.py" in page

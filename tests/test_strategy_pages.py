from dominion.reporting.strategy_links import strategy_page_href, strategy_slug
from dominion.reporting.strategy_pages import (
    RenderedStrategy,
    render_strategy_leaderboard,
    render_strategy_page,
    render_strategy_pages,
)
from dominion.reporting.html_report import (
    _strategy_report_href,
    generate_leaderboard_html,
)
from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


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
        _strategy_report_href("strategy_20260212_094841", prefix="strategies")
        == "strategies/strategy20260212-094841.html"
    )


def test_strategy_page_renders_bounty_hunter_exile_override():
    strategy = EnhancedStrategy()
    strategy.name = "Copper Before Curse"
    strategy.bounty_hunter_exile_priority = [
        PriorityRule("Copper"),
        PriorityRule("Curse"),
    ]
    item = RenderedStrategy(
        display_name=strategy.name,
        slug="copper-before-curse",
        strategy=strategy,
        source_path="example.py",
        factory_name="create_example",
        references={},
    )

    html = render_strategy_page(item)

    assert "Bounty Hunter Exile Priority" in html
    section = html.split("Bounty Hunter Exile Priority", 1)[1]
    assert section.index("Copper") < section.index("Curse")


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
            "unregistered_strategy": {
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
    assert "unregistered_strategy.html" not in html
    assert "<td>unregistered_strategy</td>" in html


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
        "card-strategy-usage.html",
        "big-money.html",
        "random-unused-card-kingdom-guide.html",
        "cursed-band-biding-time-strategy-guide.html",
        "tea-house-kind-emperor-strategy-guide.html",
        "mine-guildhall-strategy-guide.html",
        "kimberley-mine-engine-strategy-guide.html",
        "hyderabad-strategy-guide.html",
        "lisbon-strategy-guide.html",
        "oslo-strategy-guide.html",
        "port-moresby-strategy-guide.html",
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
        "card-strategy-usage.html",
        "big-money.html",
        "random-unused-card-kingdom-guide.html",
        "cursed-band-biding-time-strategy-guide.html",
        "tea-house-kind-emperor-strategy-guide.html",
        "mine-guildhall-strategy-guide.html",
        "kimberley-mine-engine-strategy-guide.html",
        "hyderabad-strategy-guide.html",
        "lisbon-strategy-guide.html",
        "oslo-strategy-guide.html",
        "port-moresby-strategy-guide.html",
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


def test_strategy_page_lists_overridden_decision_hooks(tmp_path):
    render_strategy_pages(
        tmp_path,
        names=["Oslo Workers Village Magnate Multi Colony Engine", "Big Money"],
    )

    page = (
        tmp_path / "oslo-workers-village-magnate-multi-colony-engine.html"
    ).read_text(encoding="utf-8")

    assert "Custom Behaviors" in page
    assert "Choose anvil gain" in page
    assert "Gain whichever of Village/Magnate is further below its target ratio." in page
    assert "Choose action" in page
    assert "preserve a payload" in page

    plain_page = (tmp_path / "big-money.html").read_text(encoding="utf-8")
    assert "Custom Behaviors" not in plain_page


def test_custom_gain_policy_is_not_presented_as_unconditional_buy_order():
    from generated_strategies.tea_house_kind_emperor import TeaHouseEmperor

    # Inherited overrides also control decisions.
    class InheritedEngine(TeaHouseEmperor):
        pass

    item = RenderedStrategy(
        display_name="Tea House and Kind Emperor",
        slug="tea-house-kind-emperor",
        strategy=InheritedEngine(),
        source_path="generated_strategies/tea_house_kind_emperor.py",
        factory_name="create_tea_house_kind_emperor",
        references={},
    )
    page = render_strategy_page(item)
    gain = page.split('class="section section-gain"', 1)[1].split('</section>', 1)[0]

    assert "Gain Decisions" in gain
    assert "Gain Priority" not in gain
    assert "Custom decision logic controls these choices" in gain
    assert '<details class="technical-details"><summary>Static list' in gain
    assert "No list condition" in gain
    assert "Always" not in gain
    assert 'href="tea-house-kind-emperor-strategy-guide.html"' in page
    # The treasure policy is not overridden and still uses its priority list.
    assert "Treasure Priority" in page
    assert "earlier eligible rows still take precedence" in page


def test_base_gain_policy_discloses_collection_and_butterfly_rewrites():
    from dominion.cards.registry import get_card
    from dominion.game.game_state import GameState
    from dominion.game.player_state import PlayerState

    strategy = EnhancedStrategy()
    strategy.gain_priority = [PriorityRule("Silver"), PriorityRule("Village")]
    player = PlayerState(ai=None, collection_played=1)
    state = GameState(players=[player], supply={"Silver": 40, "Village": 10})
    choices = [get_card("Silver"), get_card("Village")]
    # The shared gain policy can choose a later row, even with no override.
    assert strategy.choose_gain(state, player, choices).name == "Village"

    page = render_strategy_page(RenderedStrategy(
        display_name="Collection Action Gains", slug="collection-action-gains",
        strategy=strategy, source_path="example.py", factory_name="create_example",
        references={},
    ))
    gain = page.split('class="section section-gain"', 1)[1].split('</section>', 1)[0]
    assert "Gain Priority" in gain
    assert "Shared gain logic can change the list choice" in gain
    assert "Collection" in gain
    assert "Way of the Butterfly" in gain
    assert "within the list" in gain


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


def test_card_expansion_comes_from_the_defining_card_package():
    from dominion.reporting.strategy_pages import card_expansion

    assert card_expansion("Torturer") == "Intrigue"
    assert card_expansion("Gold") == "Base"
    assert card_expansion("Province") == "Base"
    assert card_expansion("Not A Real Card") is None


def test_card_expansion_overrides_win_over_the_defining_package():
    # These cards are implemented under a different expansion's package than
    # the set they belong to; the override table must win over the package.
    from dominion.reporting.strategy_pages import card_expansion

    assert card_expansion("Astrolabe") == "Seaside"
    assert card_expansion("Collection") == "Prosperity"
    assert card_expansion("Fisherman") == "Menagerie"
    assert card_expansion("Highwayman") == "Allies"
    assert card_expansion("Mill") == "Intrigue"
    assert card_expansion("Pilgrim") == "Plunder"
    assert card_expansion("Snowy Village") == "Menagerie"
    assert card_expansion("Taskmaster") == "Plunder"
    assert card_expansion("Trading Post") == "Intrigue"
    assert card_expansion("Wandering Minstrel") == "Dark Ages"
    assert card_expansion("Wealthy Village") == "Plunder"


def test_card_expansion_overrides_only_name_registered_misfiled_cards():
    from dominion.cards.registry import get_card
    from dominion.reporting.strategy_pages import (
        _CARD_EXPANSION_OVERRIDES,
        _EXPANSION_LABELS,
    )

    for name, expansion in _CARD_EXPANSION_OVERRIDES.items():
        # A typo in the key would silently make the override dead code.
        card = get_card(name)
        assert card.name == name
        # An override that agrees with the defining package is redundant and
        # suggests the card module was moved without pruning the table.
        package = type(card).__module__.split(".")[2]
        package_label = _EXPANSION_LABELS.get(
            package, package.replace("_", " ").title()
        )
        assert expansion != package_label, name


def test_strategy_leaderboard_rows_carry_card_and_expansion_filter_data():
    html = render_strategy_leaderboard(
        {
            "Torture Campaign": {
                "wins": 9,
                "losses": 1,
                "win_rate": 90.0,
                "description": "Torturer engine.",
                "cards": ["Inn", "Torturer"],
            },
            "Big Money": {
                "wins": 1,
                "losses": 9,
                "win_rate": 10.0,
                "description": "Simple treasure strategy.",
                "cards": ["Gold", "Province"],
            },
        }
    )

    assert (
        'class="leaderboard-row" data-cards="Inn|Torturer" '
        'data-expansions="Hinterlands|Intrigue" data-win-rate="90.0" data-record="9-1"'
    ) in html
    assert 'data-cards="Gold|Province" data-expansions="Base"' in html
    # The filter panel offers every card and expansion seen in the standings.
    assert 'id="leaderboard-card-form"' in html
    assert '<option value="Torturer"></option>' in html
    assert '<option value="Province"></option>' in html
    for expansion in ("Base", "Hinterlands", "Intrigue"):
        assert f'class="expansion-toggle" data-expansion="{expansion}"' in html
    assert "Showing all 2 strategies." in html
    assert 'id="leaderboard-filter-empty"' in html
    assert "querySelectorAll('.leaderboard-row')" in html


def test_strategy_leaderboard_without_results_has_no_filter_panel():
    html = render_strategy_leaderboard({})

    assert 'id="leaderboard-filters"' not in html
    assert "leaderboard-row" not in html

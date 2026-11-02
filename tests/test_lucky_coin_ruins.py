"""Scenario setup and rule interactions essential to the Ruins strategy search."""

from collections import Counter

import pytest

from dominion.cards.registry import get_card
from generated_strategies.lucky_coin_ruins import START
from scripts.search_lucky_coin_ruins import setup


def test_exact_scenario_start_and_landscapes():
    s = setup({}, {}, 123)
    for p in s.players:
        assert Counter(c.name for c in p.all_cards()) == Counter(START)
        assert len(p.hand) == 5
    assert s.supply["Province"] == 8
    assert s.supply["Copper"] == 52
    assert s.prophecy.name == "Kind Emperor"
    assert s.sun_tokens == 5
    assert [e.name for e in s.events] == ["Banquet", "Scrounge"]
    assert all(
        s.supply[n] == 4 for n in ["Battle Plan", "Archer", "Warlord", "Territory"]
    )


def test_lucky_coin_triggers_shrine_before_coppers_are_played():
    s = setup({}, {}, 123)
    p = s.current_player
    shrine, coin, ruin, copper = map(
        get_card, ["Secluded Shrine", "Lucky Coin", "Survivors", "Copper"]
    )
    p.deck = [get_card("Silver") for _ in range(3)]
    p.discard = []
    p.hand = [shrine, coin, ruin, copper]
    p.in_play = []
    s.phase = "action"
    s.handle_action_phase()
    s.handle_treasure_phase()
    assert ruin in s.trash
    assert copper in s.trash
    assert coin in p.in_play
    assert any(c.name == "Silver" for c in p.discard)


@pytest.mark.parametrize("decline", [False, True])
def test_mining_road_allowances_stack_and_declining_preserves_them(decline):
    s = setup({}, {}, 123)
    p = s.current_player
    p.coins = 0
    road = get_card("Mining Road")
    road.play_effect(s)
    road.play_effect(s)  # A replay supplies another allowance.
    p.ai.strategy.should_play_mining_road_treasure = lambda *args: not decline
    for _ in range(3):
        s.gain_from_supply(p, "Silver")
    assert p.mining_road_uses == (2 if decline else 0)
    assert p.coins == (0 if decline else 4)
    assert sum(c.name == "Silver" for c in p.in_play) == (0 if decline else 2)


def test_banquet_uses_free_gain_policy_and_respects_exposed_pile():
    s = setup({}, {}, 123)
    p = s.current_player

    def gain(s, p, choices, context):
        assert context.source == "Banquet"
        assert not {"Archer", "Warlord", "Territory", "Daimyo"} & {
            c.name for c in choices
        }
        return next(c for c in choices if c.name == "Lost City")

    p.ai.strategy.choose_free_gain = gain
    before = s.supply["Lost City"]
    s.events[0].on_buy(s, p)
    assert s.supply["Lost City"] == before - 1


def test_kind_emperor_can_gain_daimyo_without_debt():
    s = setup(dict(free="daimyo", shrine=0, lost=0), {}, 123)
    p = s.current_player
    s.prophecy.on_turn_start(s, p)
    assert any(c.name == "Daimyo" for c in p.hand)
    assert p.debt == 0


def test_fool_transfers_the_unique_lost_in_the_woods_state():
    s = setup({}, {}, 123)
    p, other = s.players
    other.lost_in_the_woods = True
    get_card("Fool").play_effect(s)
    assert p.lost_in_the_woods
    assert not other.lost_in_the_woods


def test_warlord_policy_rotates_the_clashes_pile():
    s = setup(dict(battle=1, warlord=1), {}, 123)
    get_card("Battle Plan").play_effect(s)
    assert get_card("Archer").may_be_bought(s)
    get_card("Battle Plan").play_effect(s)
    assert get_card("Warlord").may_be_bought(s)


def test_mining_road_allowances_expire_before_start_of_turn_gains(monkeypatch):
    s = setup({}, {}, 123)
    p = s.current_player
    p.mining_road_uses = 2
    observed = []

    def start_hook(player, reason):
        if reason == "start_of_turn":
            observed.append(player.mining_road_uses)
            silver = get_card("Silver")
            s.gain_card(player, silver)
            assert silver in player.discard

    monkeypatch.setattr(s, "_call_tavern_triggers", start_hook)
    s.play_turn()
    assert observed == [0]


def test_cleanup_uses_last_action_for_shrine_before_highwayman():
    s = setup(dict(cleanup={}, shrine=1), {}, 123)
    p = s.current_player
    p.hand = [
        get_card(n)
        for n in ["Highwayman", "Secluded Shrine", "Survivors", "Lucky Coin"]
    ]
    p.actions = 1
    choices = p.hand + [None]
    assert p.ai.strategy.choose_action(s, p, choices).name == "Secluded Shrine"


def test_cleanup_holds_ruins_for_banquet_trigger_without_lucky_coin():
    s = setup(dict(cleanup={}, shrine=1), {}, 123)
    p = s.current_player
    p.hand = [
        get_card(n)
        for n in [
            "Secluded Shrine",
            "Survivors",
            "Ruined Market",
            "Copper",
            "Copper",
            "Copper",
        ]
    ]
    p.deck = []
    p.discard = []
    p.in_play = []
    p.actions = 3
    p.coins = 0
    p.buys = 1
    p.turns_taken = 3
    s.phase = "action"
    s.handle_action_phase()
    assert all(
        any(c.name == name for c in p.hand) for name in ["Survivors", "Ruined Market"]
    )
    s.handle_treasure_phase()
    s.handle_buy_phase()
    assert {"Survivors", "Ruined Market"} <= {c.name for c in s.trash}
    assert any(c.name == "Tea House" for c in p.discard)


def test_cleanup_can_buy_copper_to_activate_shrine_when_banquet_unaffordable():
    s = setup(dict(cleanup={}, shrine=1), {}, 123)
    p = s.current_player
    p.hand = [
        get_card(n) for n in ["Secluded Shrine", "Survivors", "Ruined Market", "Copper"]
    ]
    p.deck = []
    p.discard = []
    p.in_play = []
    p.actions = 1
    p.coins = 0
    p.buys = 1
    p.turns_taken = 3
    s.phase = "action"
    s.handle_action_phase()
    s.handle_treasure_phase()
    assert p.coins == 2
    s.handle_buy_phase()
    assert {"Survivors", "Ruined Market"} <= {c.name for c in s.trash}


def test_cleanup_preserves_a_province_buy_when_trashing_copper():
    s = setup(dict(cleanup=dict(reserve="breakpoints")), {}, 123)
    p = s.current_player
    p.hand = [get_card("Copper")]
    p.coins = 7
    s.phase = "treasure"
    assert p.ai.strategy.choose_trash(s, p, p.hand + [None]) is None
    p.coins = 8
    assert p.ai.strategy.choose_trash(s, p, p.hand + [None]).name == "Copper"


def test_free_shrine_policy_requires_lucky_coin_and_two_ruins_in_hand():
    s = setup(dict(cleanup=dict(free_shrine="coin"), shrine=0, lost=0), {}, 123)
    p = s.current_player
    p.hand = [
        get_card(n) for n in ["Lucky Coin", "Survivors", "Ruined Market", "Copper"]
    ]
    choices = [get_card(n) for n in ["Secluded Shrine", "Tea House", "Daimyo"]]
    assert (
        p.ai.strategy.choose_kind_emperor_gain(s, p, choices).name == "Secluded Shrine"
    )
    p.hand = [c for c in p.hand if c.name != "Lucky Coin"]
    assert p.ai.strategy.choose_kind_emperor_gain(s, p, choices).name == "Tea House"


def test_shrine_saves_surplus_copper_for_buy_phase_trashing():
    s = setup(
        dict(cleanup=dict(hold_copper=True, reserve="breakpoints"), shrine=1), {}, 123
    )
    p = s.current_player
    p.hand = [get_card(n) for n in ["Ruined Village", "Copper", "Copper", "Highwayman"]]
    p.deck = []
    p.discard = []
    shrine = get_card("Secluded Shrine")
    shrine.shrine_charges = 1
    p.in_play = [shrine]
    p.duration = [shrine]
    p.coins = 1
    p.buys = 1
    p.highwayman_attacks = 1
    p.turns_taken = 6
    s.phase = "treasure"
    s.handle_treasure_phase()
    assert sum(c.name == "Copper" for c in p.hand) == 1
    assert p.coins == 1
    s.handle_buy_phase()
    assert {"Ruined Village", "Copper"} <= {c.name for c in s.trash}
    assert p.bought_this_turn == ["Copper"]


def test_shrine_copper_hold_preserves_province_purchase_and_random_state():
    import random

    s = setup(
        dict(cleanup=dict(hold_copper=True, reserve="breakpoints"), shrine=1, green=0),
        {},
        123,
    )
    p = s.current_player
    p.hand = [get_card("Copper")]
    shrine = get_card("Secluded Shrine")
    shrine.shrine_charges = 1
    p.in_play = [shrine]
    p.duration = [shrine]
    p.coins = 7
    p.buys = 1
    p.turns_taken = 6
    s.phase = "treasure"
    before = random.getstate()
    assert p.ai.strategy.copper_hold_plan(s, p) == 0
    assert random.getstate() == before
    assert p.coins == 7 and len(p.hand) == 1
    s.handle_treasure_phase()
    s.handle_buy_phase()
    assert p.bought_this_turn == ["Province"]


def test_shrine_banquet_trashes_unplayed_copper_without_losing_purchase():
    s = setup(
        dict(cleanup=dict(hold_copper=True, reserve="breakpoints"), shrine=1), {}, 123
    )
    p = s.current_player
    p.hand = [get_card("Copper"), get_card("Survivors")]
    p.deck = []
    p.discard = []
    shrine = get_card("Secluded Shrine")
    shrine.shrine_charges = 1
    p.in_play = [shrine]
    p.duration = [shrine]
    p.coins = 3
    p.buys = 1
    p.turns_taken = 6
    s.phase = "treasure"
    s.handle_treasure_phase()
    assert any(c.name == "Copper" for c in p.hand)
    assert p.coins == 3
    s.handle_buy_phase()
    assert p.bought_this_turn == ["Banquet"]
    assert {"Copper", "Survivors"} <= {c.name for c in s.trash}


def test_shrine_mining_road_income_can_precede_copper_trash():
    s = setup(
        dict(cleanup=dict(mining_first=True, reserve="breakpoints"), shrine=1), {}, 123
    )
    p = s.current_player
    p.hand = [get_card("Lucky Coin"), get_card("Copper")]
    p.deck = []
    p.discard = []
    shrine = get_card("Secluded Shrine")
    shrine.shrine_charges = 1
    road = get_card("Mining Road")
    p.in_play = [shrine, road]
    p.duration = [shrine]
    p.mining_road_uses = 1
    p.coins = 3
    s.phase = "treasure"
    s.handle_treasure_phase()
    assert any(c.name == "Copper" for c in s.trash)
    assert p.coins == 6


@pytest.mark.parametrize("swap", [False, True])
def test_shrine_trace_instrumentation_preserves_game_result(swap):
    import json
    from pathlib import Path
    from scripts.audit_lucky_coin_shrine import audit_game
    from scripts.search_lucky_coin_cleanup import CHAMPION

    spec = json.loads(
        Path("scripts/data/lucky_coin_ruins/cleanup-validation-specs.json").read_text()
    )[0]
    audited = audit_game(spec, 5000028, swap)
    s = setup(spec, CHAMPION, 5000028, swap)
    while not s.is_game_over() and s.turn_number < 160:
        s.play_turn()
    assert audited["result"] == [
        (p.get_victory_points(), p.turns_taken) for p in s.players
    ]


def test_chunked_shrine_comparison_matches_single_run_statistics():
    from scripts.compare_lucky_coin_shrine import aggregate
    from scripts.search_lucky_coin_cleanup import CHAMPION
    from scripts.search_lucky_coin_ruins import match

    spec = dict(
        opening="Secluded Shrine",
        shrine=1,
        lost=0,
        highway=1,
        daimyo=2,
        green=1,
        cleanup=dict(hold_copper=True, mining_first=True, reserve="breakpoints"),
    )
    full = match((spec, CHAMPION, 8, 1234))
    parts = [match((spec, CHAMPION, 4, 1234)), match((spec, CHAMPION, 4, 1236))]
    merged = aggregate(spec, parts)
    assert merged["rate"] == full["rate"]
    assert merged["ci95"] == pytest.approx(full["ci95"])
    assert merged["wins"] == full["wins"] and merged["ties"] == full["ties"]
    assert merged["scores"] == pytest.approx(full["scores"])
    assert merged["deck"] == pytest.approx(full["deck"])

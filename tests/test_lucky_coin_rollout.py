"""Information boundaries, exact replay, and legal alternatives for lookahead."""

import copy
import random

from dominion.ai.lucky_coin_rollout import (
    RolloutController,
    determinize,
    public_observation,
)
from dominion.cards.registry import get_card
from scripts.research_lucky_coin_rollout import policies
from scripts.search_lucky_coin_ruins import setup


def card_names(cards):
    return [c.name for c in cards]


def test_hidden_sampling_is_invariant_to_the_actual_hidden_order_and_hand():
    a, b = policies()
    s = setup(a, b, 123)
    other = copy.deepcopy(s)
    other.players[0].deck.reverse()
    pool = other.players[1].hand + other.players[1].deck
    pool.reverse()
    other.players[1].hand = pool[:5]
    other.players[1].deck = pool[5:]
    assert public_observation(s, s.players[0]) == public_observation(
        other, other.players[0]
    )
    determinize(s, 0, 789)
    determinize(other, 0, 789)
    for x, y in zip(s.players, other.players):
        assert card_names(x.hand) == card_names(y.hand)
        assert card_names(x.deck) == card_names(y.deck)


def test_hidden_sampling_preserves_observed_top_cards():
    a, b = policies()
    s = setup(a, b, 123)
    p = s.players[0]
    p.deck = [get_card(n) for n in ["Copper", "Estate", "Silver", "Gold"]]
    determinize(s, 0, 987, ["Gold", "Silver"])
    assert card_names(p.deck[-2:]) == ["Silver", "Gold"]


def test_known_top_memory_expires_on_shuffle_and_tracks_draws():
    a, b = policies()
    s = setup(a, b, 123)
    c = RolloutController(enabled=(False, False))
    c.install(s)
    c.begin(s)
    p = s.players[0]
    silver, gold = get_card("Silver"), get_card("Gold")
    p.deck = [silver, gold]
    c.observe_top(s, p, [gold, silver])
    assert c.known_top(s, p) == ["Gold", "Silver"]
    p.draw_cards(1)
    assert c.known_top(s, p) == ["Silver"]
    p.discard = [gold]
    p.shuffle_discard_into_deck()
    assert c.known_top(s, p) == []


def capture_buy():
    a, b = policies()
    s = setup(a, b, 123)
    p = s.current_player
    p.coins = 5
    p.buys = 1
    p.turns_taken = 4
    s.phase = "buy"
    saved = []
    c = RolloutController(enabled=(False, False), observer=saved.append)
    c.install(s)
    c.begin(s)
    s.play_turn()
    return s, c, next(d for d in saved if d.kind == "buy")


def test_purchase_alternatives_include_cleanup_debt_cards_and_passing():
    _, _, d = capture_buy()
    assert {
        "Secluded Shrine",
        "Spice Merchant",
        "Daimyo",
        "Tea House",
        "Banquet",
        "pass",
    } <= set(d.options)


def test_rollout_is_pure_and_cannot_use_actual_unseen_order():
    s, c, d = capture_buy()
    before = random.getstate()
    root_zones = [
        (card_names(p.hand), card_names(p.deck), card_names(p.discard))
        for p in s.players
    ]
    first = c.outcome(d, "Secluded Shrine", 994)
    changed = copy.deepcopy(d)
    changed.checkpoint.players[0].deck.reverse()
    opponent = changed.checkpoint.players[1]
    pool = list(reversed(opponent.hand + opponent.deck))
    opponent.hand, opponent.deck = (
        pool[: len(opponent.hand)],
        pool[len(opponent.hand) :],
    )
    assert c.outcome(changed, "Secluded Shrine", 994) == first
    assert random.getstate() == before
    assert root_zones == [
        (card_names(p.hand), card_names(p.deck), card_names(p.discard))
        for p in s.players
    ]


def test_replay_can_resume_second_shrine_trash_without_losing_pending_effects():
    a, b = policies()
    s = setup(b, a, 123)
    p = s.current_player
    p.hand = [get_card(n) for n in ["Lucky Coin", "Copper", "Silver", "Ruined Village"]]
    shrine = get_card("Secluded Shrine")
    shrine.shrine_charges = 1
    p.in_play = [shrine]
    p.duration = [shrine]
    p.turns_taken = 3
    s.phase = "treasure"
    saved = []
    c = RolloutController(enabled=(False, False), observer=saved.append)
    c.install(s)
    c.begin(s)
    s.play_turn()
    trashes = [d for d in saved if d.kind == "trash"]
    assert len(trashes) == 2
    assert {"Silver", "Copper", "pass"} <= set(trashes[1].options)
    assert c.outcome(trashes[1], "Silver", 12345) in (0.0, 0.5, 1.0)


def test_independent_verification_rejects_a_noisy_proposal(monkeypatch):
    a, b = policies()
    s = setup(a, b, 123)
    s.phase = "buy"
    s.current_player.coins = 5
    c = RolloutController(verify=8, enabled=(True, False))
    c.install(s)
    c.begin(s)
    monkeypatch.setattr(
        c, "evaluate", lambda *args: dict(choice="Daimyo", paired_delta=1, paired_se=0)
    )
    monkeypatch.setattr(c, "outcome", lambda *args: 0.5)
    choices = [get_card("Tea House"), get_card("Daimyo"), None]
    assert s.current_player.ai.choose_buy(s, choices).name == "Tea House"
    assert c.records[-1]["verification"]["paired_sign_p"] == 1


def test_independent_verification_accepts_consistent_fresh_advantage(monkeypatch):
    a, b = policies()
    s = setup(a, b, 123)
    s.phase = "buy"
    s.current_player.coins = 5
    c = RolloutController(verify=8, enabled=(True, False))
    c.install(s)
    c.begin(s)
    monkeypatch.setattr(
        c, "evaluate", lambda *args: dict(choice="Daimyo", paired_delta=1, paired_se=0)
    )
    monkeypatch.setattr(c, "outcome", lambda d, choice, seed: float(choice == "Daimyo"))
    choices = [get_card("Tea House"), get_card("Daimyo"), None]
    assert s.current_player.ai.choose_buy(s, choices).name == "Daimyo"
    assert c.records[-1]["verification"]["paired_sign_p"] == 1 / 256


def test_change_cannot_decline_mandatory_trash_or_gain():
    from tests.utils import DummyAI

    class DecliningAI(DummyAI):
        def choose_card_to_trash(self, state, choices):
            return None

        def choose_buy(self, state, choices):
            assert None not in choices
            return None

    a, b = policies()
    s = setup(a, b, 123)
    p = s.current_player
    p.ai = DecliningAI()
    copper = get_card("Copper")
    p.hand = [copper]
    p.debt = 0
    get_card("Change").play_effect(s)
    assert copper in s.trash
    assert any(c.name == "Province" for c in p.discard)
    assert p.debt == 8


def test_change_legacy_decline_requires_explicit_research_opt_in():
    from tests.utils import DummyAI

    class LegacyAI(DummyAI):
        allow_legacy_change_pass = True

        def choose_card_to_trash(self, state, choices):
            return None

    a, b = policies()
    s = setup(a, b, 123)
    p = s.current_player
    p.ai = LegacyAI()
    copper = get_card("Copper")
    p.hand = [copper]
    get_card("Change").play_effect(s)
    assert copper in p.hand and not s.trash


def test_cleanup_schedule_reserves_purchase_and_both_trash_slots(monkeypatch):
    a, b = policies()
    s = setup(a, b, 123)
    p = s.current_player
    c = RolloutController(schedule="cleanup", verify=0, enabled=(True, False))
    c.install(s)
    c.begin(s)
    searched = []

    def evaluate(d, *args, **kwargs):
        searched.append(d.kind)
        return dict(choice=d.baseline, paired_delta=0, paired_se=0)

    monkeypatch.setattr(c, "evaluate", evaluate)
    options = [get_card("Copper"), get_card("Silver"), None]
    baseline = lambda: options[0]
    for kind in ["action", "emperor", "buy", "trash", "trash", "spice_mode", "trash"]:
        c.choose(kind, s, p, options, baseline)
    assert searched == ["emperor", "buy", "trash", "trash", "spice_mode"]


def test_cleanup_treasure_search_requires_an_armed_shrine(monkeypatch):
    a, b = policies()
    s = setup(a, b, 123)
    p = s.current_player
    c = RolloutController(schedule="cleanup", verify=0, enabled=(True, False))
    c.install(s)
    c.begin(s)
    searched = []

    def evaluate(d, *args, **kwargs):
        searched.append(d.kind)
        return dict(choice=d.baseline, paired_delta=0, paired_se=0)

    monkeypatch.setattr(c, "evaluate", evaluate)
    choices = [get_card("Copper"), None]
    c.choose("treasure", s, p, choices, lambda: choices[0])
    assert not searched
    shrine = get_card("Secluded Shrine")
    shrine.shrine_charges = 1
    p.duration = [shrine]
    c.choose("treasure", s, p, choices, lambda: choices[0])
    assert searched == ["treasure"]


def test_adaptive_discovery_keeps_paired_worlds_and_honors_cap(monkeypatch):
    _, c, d = capture_buy()
    calls = []

    def outcome(decision, choice, seed):
        calls.append((choice, seed))
        if choice == "Daimyo":
            return 1.0
        return 0.0

    monkeypatch.setattr(c, "outcome", outcome)
    result = c.evaluate(d, 4, adaptive=12)
    assert result["choice"] == "Daimyo"
    assert result["paired_delta"] == 1
    assert result["paired_samples"] == 8
    assert result["discovery_rollouts"] <= 4 * len(d.options) + 12 * 3
    for choice, seed in calls:
        if choice == "Daimyo":
            assert (d.baseline, seed) in calls


def test_parallel_benchmark_pairs_seats_by_index_not_completion_order():
    from scripts.benchmark_focused_lucky_coin import summarize

    rows = [
        dict(
            index=i,
            score=int(i < 2),
            rollouts=0,
            search_counts={},
            changed_counts={},
            proposals={},
        )
        for i in [0, 2, 1, 3]
    ]
    result = summarize(rows)
    assert result["first_policy_win_share"] == 0.5
    assert result["ci95"] == [0, 1]
    assert [r["index"] for r in result["results"]] == [0, 1, 2, 3]


def test_trash_confirmation_matches_json_round_tripped_observations(monkeypatch):
    import json
    from types import SimpleNamespace

    from scripts import confirm_lucky_coin_trash_changes as confirmation

    d = SimpleNamespace(
        identifier={"seed": 123},
        kind="trash",
        options=["Copper", "pass"],
        observation={"hand": [("Copper", 2)]},
        baseline="Copper",
    )

    def replay(*args, observer, **kwargs):
        observer(d)
        return {"score": 1}

    monkeypatch.setattr(confirmation, "play", replay)
    monkeypatch.setattr(
        RolloutController,
        "outcome",
        lambda self, d, choice, seed: float(choice == "pass"),
    )
    benchmark = dict(
        config={},
        matchups={
            "shrine-mirror": {
                "results": [
                    dict(
                        seed=123,
                        swap=False,
                        score=1,
                        changed_decisions=[
                            dict(
                                kind="trash",
                                identifier=d.identifier,
                                observation=json.loads(json.dumps(d.observation)),
                                baseline="Copper",
                                choice="pass",
                            )
                        ],
                    )
                ]
            }
        },
    )
    result = confirmation.confirm(benchmark, 2)
    assert result["results"][0]["delta"] == 1
    assert result["independent_sample_salt"] == 4

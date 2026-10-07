"""Check the free-gain policy through actual Cobbler duration resolution."""

from dominion.ai.genetic_ai import GeneticAI
from dominion.cards.registry import get_card
from dominion.strategy.strategies.cobbler_shepherd import create_cobbler_shepherd_growth
from dominion.strategy.strategies.shepherd_tragic_hero import ShepherdTragicHero
from scripts.search_cobbler_shepherd import BASELINE, match
from scripts.search_shepherd_tragic_hero import (
    candidates,
    cobbler_combinations,
    policy_key,
    refinement_parents,
)
from tests.test_shepherd_tragic_hero_rules import setup


def resolve_cobbler(policy, cards, provinces=8):
    state, player = setup(GeneticAI(policy))
    state.supply["Province"] = provinces
    player.hand = [get_card(name) for name in cards]
    cobbler = get_card("Cobbler")
    player.duration = [cobbler]
    before = list(player.hand)
    cobbler.on_duration(state)
    gained = [card for card in player.hand if card not in before]
    assert len(gained) == 1
    assert gained[0] not in player.discard
    return state, player, gained[0]


def test_cobbler_gains_extra_shepherd_without_buying_more():
    policy = ShepherdTragicHero(**BASELINE, cobbler=1, cobbler_shepherds=3)
    state, player, gained = resolve_cobbler(policy, ["Shepherd", "Estate", "Silver"])
    assert gained.name == "Shepherd"
    assert state.supply["Shepherd"] == 9
    player.turns_taken = 4
    assert (
        policy.choose_gain(
            state, player, [get_card("Shepherd"), get_card("Silver")]
        ).name
        == "Silver"
    )


def test_adaptive_cobbler_supplies_draw_only_when_hand_needs_it():
    policy = ShepherdTragicHero(
        **BASELINE, cobbler=1, cobbler_shepherds=4, cobbler_adaptive=True
    )
    assert resolve_cobbler(policy, ["Estate", "Copper"])[2].name == "Shepherd"
    assert resolve_cobbler(policy, ["Shepherd", "Estate"])[2].name == "Silver"
    assert resolve_cobbler(policy, ["Copper", "Silver"])[2].name == "Silver"


def test_cobbler_switches_to_fuel_then_scoring_and_leaves_wish_alone():
    policy = ShepherdTragicHero(
        **BASELINE, cobbler=1, cobbler_shepherds=2, cobbler_estates=5
    )
    state, player, gained = resolve_cobbler(policy, ["Shepherd", "Shepherd", "Estate"])
    assert gained.name == "Estate"
    assert resolve_cobbler(policy, ["Estate"], provinces=3)[2].name == "Estate"
    assert (
        policy.choose_card_to_gain_to_hand(
            state, player, [get_card("Gold"), get_card("Shepherd")], 6
        ).name
        == "Gold"
    )


def test_cobbler_search_is_seat_balanced_and_reproducible():
    spec = dict(BASELINE, cobbler=1, cobbler_shepherds=3)
    result = match((spec, spec, 4, 321))
    assert result == match((spec, spec, 4, 321))
    assert result["rate"] == 0.5
    assert result["truncated"] == 0


def test_general_search_can_express_and_generate_validated_cobbler_strategy():
    winner = create_cobbler_shepherd_growth()
    assert isinstance(winner, ShepherdTragicHero)
    assert policy_key(winner.params) in {policy_key(p) for p in candidates()}
    # Buying and Cobbler gains must remain separate in the common policy.
    policy = ShepherdTragicHero(**winner.params)
    _, _, gained = resolve_cobbler(policy, ["Estate", "Silver"])
    assert gained.name == "Shepherd"


def test_search_covers_clean_interacting_choices_and_preserves_legacy_mode():
    assert len(candidates(40261007, legacy=True)) == 157
    combos = cobbler_combinations()
    assert len(combos) == 96
    assert all(p["monastery"] == 0 for p in combos)
    assert {
        (p["cobbler"], p["cobbler_shepherds"], p["cobbler_adaptive"]) for p in combos
    } == {(c, s, a) for c in [1, 2] for s in [2, 4, 6] for a in [False, True]}


def test_refinement_retains_gain_engine_outside_top_four():
    leaders = [(0.8 - i / 100, dict(BASELINE, hero=i)) for i in range(4)]
    engine = dict(BASELINE, cobbler=2, cobbler_shepherds=4)
    ranked = leaders + [(0.6, engine)]
    assert engine in refinement_parents(ranked)
    assert engine not in refinement_parents(ranked, legacy=True)

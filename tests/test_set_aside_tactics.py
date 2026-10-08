"""Real card plays, override contracts, card conservation, and tactical hands."""
from types import SimpleNamespace

import pytest

from dominion.ai.genetic_ai import GeneticAI
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState
from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


def setup(strategy=None, names=()):
    player = PlayerState(GeneticAI(strategy or EnhancedStrategy()))
    state = GameState([player], supply={"Province": 8, "Silver": 40, "Gold": 30, "Smithy": 10})
    state.log_callback = lambda *args: None
    player.hand = [get_card(name) for name in names]
    return state, player


def play(state, player, card):
    player.in_play.append(card)
    if card.is_action:
        player.actions -= 1
        state.play_action_indirectly(player, card)
    else:
        state.play_treasure_indirectly(player, card)


@pytest.mark.parametrize("name,hook", [
    ("Gear", "choose_gear_set_aside"), ("Haven", "choose_card_to_set_aside_for_haven"),
])
def test_override_executes_after_draw_through_engine(name, hook):
    seen = []
    strategy = EnhancedStrategy()

    def choose(state, player, choices):
        seen.append(list(choices))
        return choices[:1] if name == "Gear" else choices[0]

    setattr(strategy, hook, choose)
    state, player = setup(strategy, ("Gold",))
    gold = player.hand[0]
    player.deck = [get_card("Estate"), get_card("Copper")]
    card = get_card(name)
    play(state, player, card)
    assert len(seen[0]) == (3 if name == "Gear" else 2)
    assert card.set_aside == [gold]
    assert gold not in player.hand
    assert sum(c is gold for c in player.all_cards()) == 1
    state.do_duration_phase()
    assert sum(c is gold for c in player.hand) == 1
    assert card.set_aside == []
    assert card not in player.duration
    assert card in player.in_play  # stays through the resolving turn


@pytest.mark.parametrize("name", ["Gear", "Haven"])
def test_strategy_without_hook_uses_base_fallback(name):
    state, player = setup(SimpleNamespace(), ("Smithy", "Gold"))
    smithy = player.hand[0]
    # Haven's +Action makes Smithy playable; Gear consumes the last Action.
    player.actions = 0 if name == "Haven" else 1
    card = get_card(name)
    play(state, player, card)
    assert card.set_aside == [smithy]
    assert player.hand[0].name == "Gold"


@pytest.mark.parametrize("name", ["Gear", "Haven"])
def test_empty_hand_has_no_pending_duration(name):
    state, player = setup()
    card = get_card(name)
    play(state, player, card)
    assert card.set_aside == []
    assert card not in player.duration
    assert not card.duration_persistent
    state.handle_cleanup_phase()
    assert card not in player.in_play


@pytest.mark.parametrize("answer", [None, [], [get_card("Gold")]])
def test_gear_optional_decline_and_invalid_choices(answer):
    strategy = EnhancedStrategy()
    strategy.choose_gear_set_aside = lambda *args: answer
    state, player = setup(strategy, ("Gold",))
    gold = player.hand[0]
    gear = get_card("Gear")
    play(state, player, gear)
    assert player.hand == [gold]
    assert gear.set_aside == []
    assert gear not in player.duration


def test_gear_ignores_invalid_duplicate_and_excess_selections():
    strategy = EnhancedStrategy()
    strategy.choose_gear_set_aside = lambda s, p, c: [get_card("Gold"), c[0], c[0], c[1], c[2]]
    state, player = setup(strategy, ("Silver", "Silver", "Gold"))
    first, second, third = player.hand
    gear = get_card("Gear")
    play(state, player, gear)
    assert gear.set_aside == [first, second]
    assert player.hand == [third]


@pytest.mark.parametrize("answer", [None, get_card("Gold")])
def test_haven_invalid_override_must_choose_a_legal_card(answer):
    strategy = EnhancedStrategy()
    strategy.choose_card_to_set_aside_for_haven = lambda *args: answer
    state, player = setup(strategy, ("Gold", "Province"))
    gold, province = player.hand
    haven = get_card("Haven")
    play(state, player, haven)
    assert haven.set_aside == [province]
    assert player.hand == [gold]


def test_haven_reuses_generic_discard_override_with_reason():
    strategy = EnhancedStrategy()
    reasons = []

    def discard(state, player, choices, count, *, reason=None):
        reasons.append((count, reason))
        return [choices[-1]]

    strategy.choose_cards_to_discard = discard
    state, player = setup(strategy, ("Estate", "Copper"))
    copper = player.hand[-1]
    haven = get_card("Haven")
    play(state, player, haven)
    assert haven.set_aside == [copper]
    assert reasons == [(1, "haven")]


@pytest.mark.parametrize("name", ["Gear", "Haven"])
def test_multiple_physical_copies_keep_separate_storage(name):
    strategy = EnhancedStrategy()
    strategy.choose_gear_set_aside = lambda s, p, c: c[:1]
    strategy.choose_card_to_set_aside_for_haven = lambda s, p, c: c[0]
    state, player = setup(strategy, ("Gold", "Silver"))
    gold, silver = player.hand
    first, second = get_card(name), get_card(name)
    play(state, player, first)
    play(state, player, second)
    assert first.set_aside == [gold]
    assert second.set_aside == [silver]
    state.do_duration_phase()
    assert player.hand == [gold, silver]
    state.do_duration_phase()
    assert player.hand == [gold, silver]


@pytest.mark.parametrize("name", ["Gear", "Haven"])
def test_throne_room_replays_accumulate_and_return_all_cards_once(name):
    strategy = EnhancedStrategy()
    strategy.action_priority = [PriorityRule(name)]
    strategy.choose_gear_set_aside = lambda s, p, c: c[:1]
    strategy.choose_card_to_set_aside_for_haven = lambda s, p, c: c[0]
    state, player = setup(strategy, (name, "Gold", "Silver"))
    target, gold, silver = player.hand
    throne = get_card("Throne Room")
    play(state, player, throne)
    assert target.set_aside == [gold, silver]
    assert len(player.all_cards()) == 4
    state.handle_cleanup_phase()
    assert target in player.duration
    assert throne in player.in_play
    state.do_duration_phase()
    assert player.hand == [gold, silver]
    assert not target.duration_persistent
    assert target not in player.duration
    state.handle_cleanup_phase()
    assert throne not in player.in_play
    assert target not in player.in_play


@pytest.mark.parametrize("name", ["Gear", "Haven"])
def test_empty_replay_preserves_earlier_set_aside(name):
    strategy = EnhancedStrategy()
    strategy.choose_gear_set_aside = lambda s, p, c: c[:1]
    state, player = setup(strategy, ("Gold",))
    gold = player.hand[0]
    card = get_card(name)
    play(state, player, card)
    state.play_action_indirectly(player, card)
    assert card.set_aside == [gold]
    state.do_duration_phase()
    assert player.hand == [gold]


@pytest.mark.parametrize("names,actions,expected", [
    (("Gold", "Silver"), 0, []),  # preserve the $5 buy
    (("Gold", "Gold", "Copper"), 0, ["Copper"]),  # preserve $6
    (("Estate", "Province"), 0, []),  # no next-hand value
    (("Smithy", "Smithy", "Gold"), 1, ["Smithy"]),  # excessive terminals
    (("Village", "Smithy", "Smithy"), 1, []),  # action support available
    (("Smithy", "Gold"), 0, ["Smithy"]),
    (("Laboratory", "Copper"), 0, ["Laboratory"]),
    (("Copper", "Copper", "Copper"), 0, []),  # minimum building economy
])
def test_gear_tactical_hands(names, actions, expected):
    state, player = setup(names=names)
    player.actions = actions
    choices = player.ai.choose_gear_set_aside(state, player, list(player.hand))
    assert [c.name for c in choices] == expected


def test_gear_preserves_discounted_supply_breakpoint():
    state, player = setup(names=("Gold", "Gold", "Copper"))
    player.cost_reduction = 1  # Province now costs $7
    assert player.ai.choose_gear_set_aside(state, player, player.hand) == []


def test_endgame_keeps_money_for_last_province_and_haven_sacrifices_junk():
    state, player = setup(names=("Gold", "Gold", "Silver", "Smithy", "Estate"))
    state.supply["Province"] = 1
    player.actions = 0
    assert player.ai.choose_gear_set_aside(state, player, player.hand) == []
    pick = player.ai.choose_card_to_set_aside_for_haven(state, player, player.hand)
    assert pick.name == "Estate"


def test_discard_preserves_money_ahead_of_expensive_dead_victory():
    state, player = setup(names=("Gold", "Copper", "Province", "Estate", "Curse"))
    picks = player.ai.choose_cards_to_discard(state, player, player.hand, 3, reason="militia")
    assert [c.name for c in picks] == ["Curse", "Estate", "Province"]


def test_chapel_conditional_trash_stops_at_minimum_deck_economy():
    strategy = EnhancedStrategy()
    strategy.trash_priority = [PriorityRule("Estate"), PriorityRule(
        "Copper", lambda s, p: sum(c.stats.coins for c in p.all_cards() if c.is_treasure) > 3,
    )]
    state, player = setup(strategy, ("Estate", "Copper", "Copper", "Copper", "Copper"))
    play(state, player, get_card("Chapel"))
    assert [c.name for c in state.trash] == ["Estate", "Copper"]
    assert [c.name for c in player.hand] == ["Copper"] * 3


@pytest.mark.parametrize("answer", [None, get_card("Copper")])
def test_chapel_invalid_or_stop_keeps_hand(answer):
    strategy = EnhancedStrategy()
    strategy.choose_trash = lambda *args: answer
    state, player = setup(strategy, ("Copper",))
    copper = player.hand[0]
    play(state, player, get_card("Chapel"))
    assert player.hand == [copper]
    assert state.trash == []


@pytest.mark.parametrize("answer", [None, get_card("Gold")])
def test_junk_dealer_mandatory_invalid_fallback_preserves_useful_economy(answer):
    strategy = EnhancedStrategy()
    strategy.choose_card_to_trash_with_junk_dealer = lambda *args: answer
    state, player = setup(strategy, ("Silver", "Estate", "Copper"))
    play(state, player, get_card("Junk Dealer"))
    assert [c.name for c in state.trash] == ["Estate"]
    assert [c.name for c in player.hand] == ["Silver", "Copper"]


def test_junk_dealer_without_junk_still_trashes_one():
    state, player = setup(names=("Gold", "Silver"))
    play(state, player, get_card("Junk Dealer"))
    assert [c.name for c in state.trash] == ["Silver"]
    assert [c.name for c in player.hand] == ["Gold"]


@pytest.mark.parametrize("answer", [None, get_card("Copper")])
def test_anvil_optional_discard_validates_physical_identity(answer):
    strategy = EnhancedStrategy()
    strategy.choose_anvil_treasure_to_discard = lambda *args: answer
    state, player = setup(strategy, ("Copper",))
    copper = player.hand[0]
    play(state, player, get_card("Anvil"))
    assert player.hand == [copper]
    assert player.discard == []
    assert state.supply["Silver"] == 40


def test_anvil_existing_discard_override_and_gain_override_execute():
    strategy = EnhancedStrategy()
    strategy.choose_anvil_gain = lambda s, p, c: next(c for c in c if c.name == "Silver")
    strategy.choose_anvil_treasure_to_discard = lambda s, p, c: c[0]
    state, player = setup(strategy, ("Copper", "Gold"))
    play(state, player, get_card("Anvil"))
    assert [c.name for c in player.hand] == ["Gold"]
    assert [c.name for c in player.discard] == ["Copper", "Silver"]


def test_discard_preserves_night_cards_and_live_victory_hybrids():
    state, player = setup(names=("Guardian", "Farm", "Nobles", "Copper", "Province"))
    picks = player.ai.choose_cards_to_discard(state, player, player.hand, 2, reason="militia")
    assert [c.name for c in picks] == ["Province", "Copper"]


def test_haven_stored_victory_card_still_counts_for_scoring():
    state, player = setup(names=("Province",))
    province = player.hand[0]
    haven = get_card("Haven")
    play(state, player, haven)
    assert haven.set_aside == [province]
    assert player.get_victory_points() == 6
    assert sum(c is province for c in player.all_cards()) == 1


def test_chapel_caps_trashes_at_four_and_strategy_can_preserve_endgame_points():
    strategy = EnhancedStrategy()
    strategy.trash_priority = [PriorityRule("Estate", PriorityRule.provinces_left(">", 2))]
    state, player = setup(strategy, ("Estate",) * 5)
    play(state, player, get_card("Chapel"))
    assert len(state.trash) == 4
    state.supply["Province"] = 1
    play(state, player, get_card("Chapel"))
    assert len(player.hand) == 1
    assert len(state.trash) == 4


def test_generic_multi_trash_reuses_single_hook_and_stops_on_invalid_identity():
    strategy = EnhancedStrategy()
    calls = []

    def trash(state, player, choices):
        calls.append(list(choices))
        return choices[0] if len(calls) == 1 else get_card("Copper")

    strategy.choose_trash = trash
    state, player = setup(strategy, ("Copper", "Copper"))
    first, second = player.hand
    assert player.ai.choose_cards_to_trash(state, list(player.hand), 4) == [first]
    assert calls == [[first, second], [second]]


def test_junk_dealer_specific_override_can_choose_expensive_treasure():
    strategy = EnhancedStrategy()
    strategy.choose_card_to_trash_with_junk_dealer = lambda s, p, c: next(c for c in c if c.name == "Gold")
    state, player = setup(strategy, ("Gold", "Estate"))
    play(state, player, get_card("Junk Dealer"))
    assert [c.name for c in state.trash] == ["Gold"]
    assert [c.name for c in player.hand] == ["Estate"]


def test_anvil_base_discard_uses_cheapest_economy_and_empty_menu_declines():
    state, player = setup(names=("Gold", "Silver", "Copper"))
    assert player.ai.choose_anvil_treasure_to_discard(state, player, player.hand).name == "Copper"
    assert player.ai.choose_anvil_treasure_to_discard(state, player, player.hand[:2]).name == "Silver"
    assert player.ai.choose_anvil_treasure_to_discard(state, player, []) is None



@pytest.mark.parametrize("actions", [0, 1])
@pytest.mark.parametrize("name", ["Crown", "Werewolf", "Militia"])
def test_storage_keeps_actions_playable_in_a_later_phase(name, actions):
    from dominion.projects.capitalism import Capitalism

    names = ["Estate", name, "Gold"]
    if actions:
        names.append("Smithy")
    state, player = setup(names=names)
    if name == "Militia":
        player.projects.append(Capitalism())
    player.actions = actions
    assert player.ai.choose_gear_set_aside(state, player, player.hand) == []


def test_gear_last_action_keeps_crown_to_double_gold_this_turn():
    state, player = setup(names=("Estate", "Crown", "Gold"))
    crown = player.hand[1]
    player.deck = [get_card("Estate"), get_card("Estate")]
    gear = get_card("Gear")
    play(state, player, gear)
    assert player.actions == 0
    assert gear.set_aside == []
    assert any(card is crown for card in player.hand)
    state.phase = "treasure"
    assert state.move_card_from_hand_to_play(player, crown)
    state.play_treasure_indirectly(player, crown)
    assert player.coins == 6



@pytest.mark.parametrize("phase", ["treasure", "buy", "night"])
@pytest.mark.parametrize("name", ["Gear", "Haven"])
def test_late_phase_storage_ignores_actions_villagers_and_villages(phase, name):
    state, player = setup(names=("Smithy", "Village", "Gold"))
    state.phase = phase
    player.actions = 5
    player.villagers = 5
    player.deck = [get_card("Estate"), get_card("Estate")]
    card = get_card(name)
    player.in_play.append(card)
    state.play_action_indirectly(player, card)
    expected = ["Smithy", "Village"] if name == "Gear" else ["Smithy"]
    assert [c.name for c in card.set_aside] == expected
    assert state.phase == phase
    assert player.actions >= 5  # Haven's +Action still cannot be spent here.
    assert player.villagers == 5


@pytest.mark.parametrize("phase", ["start", "action"])
def test_storage_keeps_actions_with_usable_villagers_and_village_support(phase):
    state, player = setup(names=("Smithy", "Village", "Gold"))
    state.phase = phase
    player.actions = 0
    player.villagers = 1
    assert player.ai.choose_gear_set_aside(state, player, player.hand) == []


@pytest.mark.parametrize("phase,expected", [
    ("action", []), ("treasure", []), ("buy", ["Crown"]), ("night", ["Crown"]),
])
def test_hybrid_storage_respects_its_remaining_play_phase(phase, expected):
    state, player = setup(names=("Crown", "Werewolf", "Gold"))
    state.phase = phase
    player.actions = 0
    picks = player.ai.choose_gear_set_aside(state, player, player.hand)
    assert [c.name for c in picks] == expected



@pytest.mark.parametrize("name", ["Gear", "Haven"])
def test_copied_set_aside_effect_initializes_per_card_storage(name):
    strategy = EnhancedStrategy()
    strategy.choose_gear_set_aside = lambda state, player, choices: choices[:1]
    strategy.choose_card_to_set_aside_for_haven = lambda state, player, choices: choices[0]
    state, player = setup(strategy, ("Gold", "Silver"))
    gold, silver = player.hand
    owner = get_card("Estate")
    player.in_play.append(owner)
    effect = type(get_card(name))
    assert not hasattr(owner, "set_aside")
    effect.play_effect(owner, state)
    effect.play_effect(owner, state)
    assert owner.set_aside == [gold, silver]
    assert len(player.all_cards()) == 3
    effect.on_duration(owner, state)
    effect.on_duration(owner, state)
    assert player.hand == [gold, silver]
    assert owner.set_aside == []
    assert not owner.duration_persistent



def bonus_play(state, player, card, entry):
    state.phase = "action"
    if entry == "main":
        player.ai.strategy.action_priority = [PriorityRule(card.name)]
        player.hand.insert(0, card)
        state.handle_action_phase()
    else:
        play(state, player, card)
    assert getattr(state, "_pending_play_context", None) is None
    assert getattr(state, "_decision_play_context", None) is None


@pytest.mark.parametrize("entry", ["main", "helper"])
@pytest.mark.parametrize("legacy", [False, True])
@pytest.mark.parametrize("name", ["Gear", "Haven"])
def test_pending_training_preserves_actual_province_breakpoint(entry, legacy, name):
    state, player = setup(names=("Gold", "Gold", "Copper", "Estate"))
    state.supply[name] = 10
    if legacy:
        player.training_pile = name
    else:
        state.add_pile_token(player, name, "+$1")
    card = get_card(name)
    bonus_play(state, player, card, entry)
    assert [c.name for c in card.set_aside] == ([] if name == "Gear" else ["Estate"])
    assert player.coins == 1
    assert sum(c.stats.coins for c in player.hand if c.is_treasure) + player.coins == 8


@pytest.mark.parametrize("entry", ["main", "helper"])
@pytest.mark.parametrize("source", ["lost_arts", "champion", "great_leader"])
def test_pending_action_bonuses_keep_smithy_playable(entry, source):
    state, player = setup(names=("Smithy", "Gold"))
    state.supply["Gear"] = 10
    if source == "lost_arts":
        state.add_pile_token(player, "Gear", "+1 Action")
    elif source == "champion":
        player.champions_in_play = 2
    else:
        from dominion.prophecies.great_leader import GreatLeader
        state.prophecy = GreatLeader()
        state.prophecy.is_active = True
    gear = get_card("Gear")
    bonus_play(state, player, gear, entry)
    assert gear.set_aside == []
    # The main loop can now play Smithy, consuming the available Action.
    if entry == "helper":
        assert player.actions >= 1
        assert any(c.name == "Smithy" for c in player.hand)


@pytest.mark.parametrize("name", ["Smithy", "Village"])
def test_future_action_token_bonuses_count_as_support(name):
    names = ("Smithy", "Smithy", "Smithy", "Gold")
    if name == "Village":
        names = ("Village", *names)
    state, player = setup(names=names)
    state.add_pile_token(player, name, "+1 Action")
    player.actions = 2
    gear = get_card("Gear")
    bonus_play(state, player, gear, "helper")
    assert gear.set_aside == []


@pytest.mark.parametrize("entry", ["main", "helper"])
@pytest.mark.parametrize("source,expected,coins", [
    ("token", ["Copper"], 2), ("legacy", [], 1), ("none", ["Copper"], 0),
])
def test_pending_harbor_bonus_respects_trigger_timing(entry, source, expected, coins):
    state, player = setup(names=("Gold", "Gold", "Copper"))
    state.supply["Gear"] = 10
    player.harbor_village_pending = 1
    if source == "token":
        state.add_pile_token(player, "Gear", "+$1")
    elif source == "legacy":
        player.training_pile = "Gear"
    gear = get_card("Gear")
    bonus_play(state, player, gear, entry)
    if entry == "main" and source == "legacy":
        expected, coins = ["Copper"], 2
    assert [c.name for c in gear.set_aside] == expected
    assert player.coins == coins


@pytest.mark.parametrize("trained", ["Militia", "Gear"])
def test_way_proxy_uses_played_card_bonus_instead_of_proxy_pile(trained):
    from dominion.ways.mouse import WayOfTheMouse
    strategy = EnhancedStrategy()
    strategy.choose_way = lambda state, player, card, ways: next(w for w in ways if w)
    state, player = setup(strategy, ("Gold", "Gold", "Copper"))
    mouse = WayOfTheMouse("Gear")
    state.ways = [mouse]
    state.add_pile_token(player, trained, "+$1")
    bonus_play(state, player, get_card("Militia"), "helper")
    assert [c.name for c in mouse.set_aside_card.set_aside] == ([] if trained == "Militia" else ["Copper"])
    assert player.coins == int(trained == "Militia")


def test_nested_storage_counts_unresolved_outer_training_once():
    strategy = EnhancedStrategy()
    strategy.action_priority = [PriorityRule("Gear")]
    state, player = setup(strategy, ("Gear", "Gold", "Gold", "Copper"))
    gear = player.hand[0]
    state.add_pile_token(player, "Throne Room", "+$1")
    bonus_play(state, player, get_card("Throne Room"), "helper")
    assert gear.set_aside == []
    assert player.coins == 1


def test_pending_context_restores_after_strategy_failure():
    strategy = EnhancedStrategy()
    def fail(*args):
        raise RuntimeError("choice failed")
    strategy.choose_gear_set_aside = fail
    state, player = setup(strategy, ("Gold",))
    with pytest.raises(RuntimeError, match="choice failed"):
        bonus_play(state, player, get_card("Gear"), "helper")
    assert getattr(state, "_pending_play_context", None) is None
    assert getattr(state, "_decision_play_context", None) is None

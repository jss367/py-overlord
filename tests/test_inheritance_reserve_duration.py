"""Current Inheritance: separate physical plays, storage and Duration ownership."""

import pytest

from dominion.cards.base_card import CardType
from dominion.cards.registry import get_card
from dominion.events.registry import get_event
from dominion.game.game_state import GameState
from dominion.projects.citadel import Citadel
from tests.utils import ChooseFirstActionAI


def new_state(target, *, replay=False, discount=0):
    state = GameState([])
    state.log_callback = lambda *_: None
    state.initialize_game([ChooseFirstActionAI()], [get_card(target)])
    pile = state.supply_pile_key(target)
    while state.top_supply_card(pile) != target:
        state.rotate_supply_pile(pile)
    player = state.players[0]
    player.hand, player.deck, player.discard = [], [], []
    player.cost_reduction = discount
    player.ai.choose_card_to_inherit = lambda *_: get_card(target)
    before = state.supply[target]
    get_event("Inheritance").on_buy(state, player)
    assert state.supply[target] == before - 1
    if replay:
        player.projects = [Citadel()]
    state.phase = "action"
    return state, player, player.inherited_action


def play_estate(state, player):
    estate = get_card("Estate")
    player.hand.insert(0, estate)
    player.actions = 1
    state.handle_action_phase()
    assert estate.name == "Estate"
    assert estate.types == [CardType.VICTORY]
    assert estate.stats.vp == 1
    return estate


@pytest.mark.parametrize("target", ["Amulet", "Caravan", "Clerk", "Dungeon", "Garrison", "Grotto", "Guide", "Island", "Mill"])
def test_every_eligible_duration_reserve_and_victory_action_can_be_inherited(target):
    state, player, physical = new_state(target)
    assert player.inherited_action_name == target
    assert physical.name == target
    assert physical in player.all_cards()
    assert state.supply[state.supply_pile_key(target)] >= 0
    assert player.cards_gained_this_turn == 0


def test_commands_are_excluded_and_cost_reduction_is_live():
    state = GameState([])
    state.log_callback = lambda *_: None
    state.initialize_game([ChooseFirstActionAI()], [get_card(n) for n in ["Captain", "Band of Misfits", "Witch", "Guide"]])
    player = state.players[0]
    player.cost_reduction = 1
    names = {c.name for c in get_event("Inheritance")._eligible_candidates(state)}
    assert "Captain" not in names and "Band of Misfits" not in names
    assert {"Guide", "Witch"} <= names


@pytest.mark.parametrize("replay", [False, True])
def test_caravan_source_stays_separate_and_retains_estate(replay):
    state, player, target = new_state("Caravan", replay=replay)
    player.deck = [get_card("Copper") for _ in range(12)]
    estate = play_estate(state, player)
    plays = 2 if replay else 1
    assert player.actions_played == 2 * plays
    assert player.duration == [target] * plays
    assert target not in player.in_play
    assert estate.duration_targets == [target]
    assert len(player.hand) == plays
    assert len(player.all_cards()) == 14
    state.handle_cleanup_phase()
    assert estate in player.in_play and target not in player.in_play
    before = len(player.hand)
    state.do_duration_phase()
    assert len(player.hand) == before + plays
    assert not player.duration
    assert target not in player.in_play and target not in player.discard
    assert player.all_cards().count(target) == 1
    state.handle_cleanup_phase()
    assert estate not in player.in_play
    assert player.all_cards().count(estate) == 1
    assert len(player.all_cards()) == 14


@pytest.mark.parametrize("target", ["Guide", "Ratcatcher", "Transmogrify", "Duplicate", "Island", "Experiment", "Feast"])
def test_source_cannot_move_itself_from_permanent_set_aside(target):
    state, player, physical = new_state(target)
    player.deck = [get_card("Copper") for _ in range(8)]
    estate = play_estate(state, player)
    assert estate in player.in_play
    assert not player.tavern_mat
    assert physical not in player.in_play + player.hand + player.deck + player.discard + state.trash
    assert player.inherited_action is physical
    assert player.all_cards().count(physical) == 1
    assert physical.get_victory_points(player) == (2 if target == "Island" else 0)


@pytest.mark.parametrize("replay", [False, True])
def test_gear_storage_belongs_to_source_and_returns_once(replay):
    state, player, target = new_state("Gear", replay=replay)
    player.ai.choose_gear_set_aside = lambda state, player, choices: choices[:1]
    player.deck = [get_card(n) for n in ["Gold", "Copper", "Silver", "Copper"]]
    estate = play_estate(state, player)
    saved = list(target.set_aside)
    assert len(saved) == (2 if replay else 1)
    assert not hasattr(estate, "set_aside")
    assert len(player.all_cards()) == 6
    state.handle_cleanup_phase()
    assert estate in player.in_play
    assert target not in player.in_play
    state.do_duration_phase()
    state.do_duration_phase()
    assert not target.set_aside and not player.duration
    assert all(player.hand.count(card) == 1 for card in saved)
    assert len(player.all_cards()) == 6
    state.handle_cleanup_phase()
    assert estate not in player.in_play


def test_gear_declining_storage_does_not_retain_estate():
    state, player, target = new_state("Gear")
    player.ai.choose_gear_set_aside = lambda *_: []
    estate = play_estate(state, player)
    assert not target.set_aside and not player.duration
    state.handle_cleanup_phase()
    assert estate not in player.in_play
    assert len(player.all_cards()) == 2


def test_two_estates_share_one_physical_source_with_distinct_plays():
    state, player, target = new_state("Caravan")
    estates = [get_card("Estate"), get_card("Estate")]
    player.hand = list(estates)
    player.deck = [get_card("Copper") for _ in range(10)]
    player.actions = 2
    state.handle_action_phase()
    assert player.actions_played == 4
    assert player.duration == [target, target]
    assert all(c.duration_targets == [target] for c in estates)
    assert player.all_cards().count(target) == 1
    state.handle_cleanup_phase()
    assert all(c in player.in_play for c in estates)
    state.do_duration_phase()
    state.handle_cleanup_phase()
    assert all(c not in player.in_play for c in estates)


def test_inherited_multiplier_retains_estate_for_its_nested_duration():
    state, player, throne = new_state("Throne Room")
    estate, caravan = get_card("Estate"), get_card("Caravan")
    player.hand = [estate, caravan]
    player.deck = [get_card("Copper") for _ in range(10)]
    player.actions = 1
    state.handle_action_phase()
    assert player.actions_played == 4
    assert throne not in player.in_play
    assert caravan in estate.duration_targets
    state.handle_cleanup_phase()
    assert estate in player.in_play
    state.do_duration_phase()
    state.handle_cleanup_phase()
    assert estate not in player.in_play


@pytest.mark.parametrize("replay", [False, True])
def test_inherited_cargo_ship_preserves_each_play_and_multiple_physical_gains(replay):
    state, player, cargo = new_state("Cargo Ship", replay=replay)
    player.ai.should_set_aside_cargo_ship = lambda *_: True
    estate = play_estate(state, player)
    gains = [state.gain_from_supply(player, n) for n in (["Gold", "Silver"] if replay else ["Gold"])]
    assert cargo.set_aside == gains
    assert cargo not in player.in_play
    assert all(card not in player.discard for card in gains)
    assert all(player.all_cards().count(card) == 1 for card in gains)
    state.handle_cleanup_phase()
    assert estate in player.in_play
    state.do_duration_phase()
    assert all(player.hand.count(card) == 1 for card in gains)
    assert cargo.set_aside == []
    state.handle_cleanup_phase()
    assert estate not in player.in_play


def test_unused_inherited_cargo_ship_instruction_expires_after_its_turn():
    state, player, cargo = new_state("Cargo Ship", replay=True)
    player.ai.should_set_aside_cargo_ship = lambda *_: True
    estate = play_estate(state, player)
    assert cargo.waiting_for_gain
    state.handle_cleanup_phase()
    assert estate not in player.in_play
    assert not cargo.waiting_for_gain
    gained = state.gain_from_supply(player, "Gold")
    assert gained in player.discard
    assert not cargo.set_aside


@pytest.mark.parametrize("target", ["Highway", "Bridge Troll"])
def test_set_aside_sources_do_not_apply_while_in_play_cost_reduction(target):
    state, player, physical = new_state(target, discount=1)
    player.cost_reduction = 0
    estate = play_estate(state, player)
    assert estate in player.in_play
    assert physical not in player.in_play
    assert state.get_card_cost(player, get_card("Gold")) == 6


def test_estate_and_source_have_separate_names_and_pile_bonuses():
    state, player, source = new_state("Smithy")
    player.deck = [get_card("Copper") for _ in range(10)]
    state.add_pile_token(player, "Estate", "+1 Card")
    state.add_pile_token(player, "Smithy", "+1 Card")
    played = []
    state.fire_ally_play_hooks = lambda p, card: played.append(card)
    estate = play_estate(state, player)
    assert played == [source, estate]
    assert len(player.hand) == 5
    assert player.actions_played == 2


def test_way_on_estate_replaces_command_instructions_without_playing_source():
    from dominion.ways.horse import WayOfTheHorse

    state, player, source = new_state("Smithy")
    state.ways = [WayOfTheHorse()]
    offers = []
    def choose(state, card, choices):
        offers.append(card)
        return choices[0]
    player.ai.choose_way = choose
    player.deck = [get_card("Copper") for _ in range(10)]
    estate = play_estate(state, player)
    assert offers == [estate]
    assert source not in player.in_play
    assert player.actions_played == 1
    assert len(player.hand) == 2


@pytest.mark.parametrize("save", [False, True])
def test_repeated_church_keeps_batches_and_each_next_turn_trash(save):
    state, player, church = new_state("Church", replay=True)
    cards = [get_card("Copper"), get_card("Silver")]
    player.hand = list(cards)
    player.ai.choose_cards_to_set_aside_for_church = lambda s, p, choices, count: choices[-1:] if save else []
    calls = []
    player.ai.choose_church_trash = lambda s, p: calls.append(list(p.hand))
    estate = play_estate(state, player)
    assert len(church.pending_batches) == 2
    assert church.set_aside == (list(reversed(cards)) if save else [])
    assert len(player.all_cards()) == 4
    state.handle_cleanup_phase()
    assert estate in player.in_play
    state.do_duration_phase()
    assert len(calls) == 2
    assert not church.pending_batches and not church.set_aside
    assert not player.duration
    assert len(player.all_cards()) == 4


def test_inherited_landing_party_cannot_move_its_source_on_a_gain():
    state, player, landing = new_state("Landing Party")
    play_estate(state, player)
    state.gain_from_supply(player, "Gold")
    assert landing not in player.deck + player.hand + player.discard + player.in_play
    assert player.inherited_action is landing


def test_repeated_archive_keeps_separate_batches_and_estates_until_both_finish():
    state, player, archive = new_state("Archive", discount=1)
    player.cost_reduction = 0
    estates = [get_card("Estate"), get_card("Estate")]
    player.hand = list(estates)
    cards = [get_card(n) for n in ["Copper", "Silver", "Gold", "Copper", "Silver", "Gold"]]
    player.deck = list(cards)
    player.actions = 2
    state.handle_action_phase()
    assert len(archive.set_aside) == 4
    assert len(archive.pending_batches) == 2
    assert all(len(batch) == 2 for batch in archive.pending_batches)
    assert len(player.all_cards()) == 9
    for remaining in [2, 0]:
        state.handle_cleanup_phase()
        assert all(c in player.in_play for c in estates)
        state.do_duration_phase()
        assert len(archive.set_aside) == remaining
        assert player.duration.count(archive) == (2 if remaining else 0)
        assert len(player.all_cards()) == 9
    state.handle_cleanup_phase()
    assert all(c not in player.in_play for c in estates)


def test_archive_short_replay_does_not_renew_the_completed_batch():
    state, player, archive = new_state("Archive", discount=1, replay=True)
    player.deck = [get_card("Copper") for _ in range(5)]
    play_estate(state, player)
    assert sorted(map(len, archive.pending_batches)) == [1, 2]
    state.handle_cleanup_phase()
    state.do_duration_phase()
    assert len(archive.set_aside) == 1
    assert player.duration == [archive]
    state.do_duration_phase()
    assert not player.duration and not archive.set_aside


def test_copied_game_keeps_inherited_cargo_ship_bound_to_copied_turn_and_owner():
    import copy

    state, player, cargo = new_state("Cargo Ship")
    player.ai.should_set_aside_cargo_ship = lambda *_: True
    estate = play_estate(state, player)
    cloned = copy.deepcopy(state)
    owner = cloned.players[0]
    copied_cargo = owner.inherited_action
    assert copied_cargo is not cargo and copied_cargo.waiting_for_gain
    gained = cloned.gain_from_supply(owner, "Gold")
    assert copied_cargo.set_aside == [gained]
    assert not cargo.set_aside
    assert estate in player.in_play
    assert owner.all_cards().count(gained) == 1

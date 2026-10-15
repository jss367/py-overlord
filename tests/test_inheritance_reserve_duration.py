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
    assert len(estate.duration_targets) == plays
    assert all(play.instruction_source is target for play in estate.duration_targets)
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
    assert all(c.duration_targets[0].instruction_source is target for c in estates)
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
    assert caravan in estate.duration_targets[0].duration_targets
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


def test_estates_do_not_share_an_earlier_multipliers_duration_dependency():
    state, player, source = new_state("Throne Room")
    first, second = get_card("Estate"), get_card("Estate")
    caravan, smithy = get_card("Caravan"), get_card("Smithy")
    player.deck = [get_card("Copper") for _ in range(20)]
    player.hand = [caravan]
    player.in_play = [first]
    player.ai.choose_action = lambda s, choices: next((c for c in choices if c is caravan), None)
    state.play_action_indirectly(player, first)
    player.hand.append(smithy)
    player.in_play.append(second)
    player.ai.choose_action = lambda s, choices: next((c for c in choices if c is smithy), None)
    state.play_action_indirectly(player, second)
    state.handle_cleanup_phase()
    assert first in player.in_play
    assert second not in player.in_play
    assert source not in player.in_play


def test_delayed_multiplier_retains_only_the_estate_that_played_a_duration():
    state, player, source = new_state("Mastermind", discount=1)
    first, second = get_card("Estate"), get_card("Estate")
    player.in_play = [first, second]
    player.deck = [get_card("Copper") for _ in range(20)]
    state.play_action_indirectly(player, first)
    state.play_action_indirectly(player, second)
    state.handle_cleanup_phase()
    caravan, smithy = get_card("Caravan"), get_card("Smithy")
    player.hand.extend([caravan, smithy])
    player.ai.choose_mastermind_action = lambda s, p, choices: next((c for c in choices if c is caravan or c is smithy), None)
    state.do_duration_phase()
    state.handle_cleanup_phase()
    assert source not in player.in_play
    assert first in player.in_play
    assert second not in player.in_play
    state.do_duration_phase()
    state.handle_cleanup_phase()
    assert first not in player.in_play


def test_only_the_estate_whose_cargo_ship_allowance_was_used_stays_out():
    state, player, source = new_state("Cargo Ship")
    player.ai.should_set_aside_cargo_ship = lambda *_: True
    first, second = get_card("Estate"), get_card("Estate")
    player.in_play = [first, second]
    state.play_action_indirectly(player, first)
    state.play_action_indirectly(player, second)
    gold = state.gain_from_supply(player, "Gold")
    assert source.set_aside == [gold]
    state.handle_cleanup_phase()
    assert first in player.in_play
    assert second not in player.in_play
    state.do_duration_phase()
    assert gold in player.hand
    state.handle_cleanup_phase()
    assert first not in player.in_play


@pytest.mark.parametrize("target", ["Grotto", "Secluded Shrine", "Crew", "Enchantress", "Secret Cave"])
def test_shared_duration_queue_has_one_pending_owner_per_estate(target):
    state, player, source = new_state(target, discount=1)
    first, second = get_card("Estate"), get_card("Estate")
    player.in_play = [first, second]
    player.hand = [get_card("Copper") for _ in range(12)]
    player.deck = [get_card("Copper") for _ in range(20)]
    player.ai.choose_cards_to_set_aside_for_grotto = lambda s, p, choices: choices[:1]
    player.ai.choose_secret_cave_discards = lambda s, p: p.hand[:3]
    state.play_action_indirectly(player, first)
    state.play_action_indirectly(player, second)
    assert player.duration.count(source) == 2
    state.handle_cleanup_phase()
    assert first in player.in_play and second in player.in_play
    if target == "Secluded Shrine":
        state.gain_from_supply(player, "Gold")
        assert source not in player.duration
        state.handle_cleanup_phase()
        assert first not in player.in_play and second not in player.in_play
    else:
        state.do_duration_phase()
        state.handle_cleanup_phase()
        assert first not in player.in_play and second not in player.in_play


def test_shared_gear_declining_a_later_play_does_not_retain_that_estate():
    state, player, source = new_state("Gear")
    first, second = get_card("Estate"), get_card("Estate")
    player.in_play = [first, second]
    player.deck = [get_card("Copper") for _ in range(10)]
    player.ai.choose_gear_set_aside = lambda s, p, choices: choices[:1]
    state.play_action_indirectly(player, first)
    player.ai.choose_gear_set_aside = lambda *_: []
    state.play_action_indirectly(player, second)
    state.handle_cleanup_phase()
    assert first in player.in_play and second not in player.in_play


def test_shared_royal_galley_keeps_each_delayed_play_with_its_estate():
    state, player, source = new_state("Royal Galley")
    first, second = get_card("Estate"), get_card("Estate")
    player.in_play = [first, second]
    player.deck = [get_card("Copper") for _ in range(30)]
    for estate in [first, second]:
        throne, smithy = get_card("Throne Room"), get_card("Smithy")
        player.hand.extend([throne, smithy])
        player.ai.choose_action = lambda s, choices, t=throne, m=smithy: next((c for c in choices if c is t or c is m), None)
        state.play_action_indirectly(player, estate)
    assert len(source.set_aside) == 2
    state.handle_cleanup_phase()
    caravan, village = get_card("Caravan"), get_card("Village")
    player.hand.extend([caravan, village])
    player.ai.choose_action = lambda s, choices: next((c for c in choices if c is caravan or c is village), None)
    state.do_duration_phase()
    assert not source.set_aside
    state.handle_cleanup_phase()
    assert first in player.in_play and second not in player.in_play
    state.do_duration_phase()
    state.handle_cleanup_phase()
    assert first not in player.in_play


def test_expired_off_turn_cargo_allowance_does_not_reactivate_on_a_later_play():
    from dominion.game.player_state import PlayerState

    state, player, source = new_state("Cargo Ship")
    other = PlayerState(ChooseFirstActionAI())
    other.inherited_action_name = "Village"
    state.players.append(other)
    state.current_player_index = 1
    player.ai.should_set_aside_cargo_ship = lambda *_: True
    first, second = get_card("Estate"), get_card("Estate")
    player.in_play = [first]
    state.play_action_as_owner_indirectly(player, first)
    old = player.virtual_gain_effects[0]
    assert old.waiting_for_gain
    state.handle_cleanup_phase()
    assert state.current_player is player
    player.in_play.append(second)
    state.play_action_indirectly(player, second)
    assert not old.waiting_for_gain
    gold = state.gain_from_supply(player, "Gold")
    assert source.set_aside == [gold]
    state.handle_cleanup_phase()
    assert first not in player.in_play and second in player.in_play


def arm_replays(state, player, pending):
    owners = []
    for name in (["Flagship", "Daimyo"] if pending == "both" else [pending]):
        card = get_card(name)
        owners.append(card)
        player.in_play.append(card)
        state.play_action_indirectly(player, card)
    return owners


@pytest.mark.parametrize("pending", ["Flagship", "Daimyo", "both"])
@pytest.mark.parametrize("route", ["main", "indirect"])
def test_pending_replays_pass_through_estate_and_play_only_the_source(pending, route):
    from dominion.ways.horse import WayOfTheHorse

    state, player, source = new_state("Smithy")
    player.deck = [get_card("Copper") for _ in range(40)]
    owners = arm_replays(state, player, pending)
    before_count, before_hand = player.actions_played, len(player.hand)
    state.add_pile_token(player, "Estate", "+1 Card")
    state.add_pile_token(player, "Smithy", "+1 Card")
    played, ways = [], []
    state.fire_ally_play_hooks = lambda p, card: played.append(card)
    state.ways = [WayOfTheHorse()]
    player.ai.choose_way = lambda s, card, choices: ways.append(card)
    if route == "main":
        estate = play_estate(state, player)
    else:
        estate = get_card("Estate")
        player.in_play.append(estate)
        state.play_action_indirectly(player, estate)
    assert played == [source] * (1 + len(owners)) + [estate]
    assert ways.count(estate) == 1 and ways.count(source) == 1 + len(owners)
    assert player.actions_played - before_count == 2 + len(owners)
    assert len(player.hand) - before_hand == 4 * (1 + len(owners)) + 1
    assert not player.flagship_pending and not player.daimyo_pending
    assert not player.daimyo_sources


@pytest.mark.parametrize("pending", ["Flagship", "Daimyo", "both"])
def test_replay_sources_and_estate_stay_for_the_inherited_duration(pending):
    state, player, source = new_state("Caravan")
    player.deck = [get_card("Copper") for _ in range(30)]
    owners = arm_replays(state, player, pending)
    estate = play_estate(state, player)
    assert player.duration.count(source) == 1 + len(owners)
    state.handle_cleanup_phase()
    assert all(card in player.in_play for card in [estate] + owners)
    state.do_duration_phase()
    state.handle_cleanup_phase()
    assert all(card not in player.in_play for card in [estate] + owners)


@pytest.mark.parametrize("pending", ["Flagship", "Daimyo", "both"])
def test_way_on_command_estate_does_not_consume_noncommand_replays(pending):
    from dominion.ways.horse import WayOfTheHorse

    state, player, source = new_state("Smithy")
    player.deck = [get_card("Copper") for _ in range(20)]
    arm_replays(state, player, pending)
    before = player.actions_played
    state.ways = [WayOfTheHorse()]
    player.ai.choose_way = lambda s, card, choices: choices[0]
    estate = play_estate(state, player)
    assert player.actions_played == before + 1
    assert source not in player.in_play
    assert estate not in player.in_play
    assert len(player.flagship_pending) == int(pending in {"Flagship", "both"})
    assert player.daimyo_pending == int(pending in {"Daimyo", "both"})


def test_inherited_garrison_cannot_hold_tokens_while_permanently_set_aside():
    state, player, source = new_state("Garrison")
    estate = play_estate(state, player)
    gold = state.gain_from_supply(player, "Gold")
    assert source.tokens == 0 and source not in player.duration
    assert source not in player.in_play
    assert player.all_cards().count(gold) == 1
    state.handle_cleanup_phase()
    assert estate not in player.in_play


def test_off_turn_daimyo_replays_the_inherited_target_on_that_actual_turn():
    from dominion.game.player_state import PlayerState

    state, player, source = new_state("Smithy")
    other = PlayerState(ChooseFirstActionAI())
    other.inherited_action_name = "Village"
    state.players.append(other)
    state.current_player_index = 1
    player.deck = [get_card("Copper") for _ in range(20)]
    daimyo, estate = get_card("Daimyo"), get_card("Estate")
    player.in_play = [daimyo, estate]
    state.play_action_as_owner_indirectly(player, daimyo)
    before = player.actions_played
    state.play_action_as_owner_indirectly(player, estate)
    assert player.actions_played - before == 3
    assert player.daimyo_pending == 0
    assert state.turn_player is other


def test_off_turn_daimyo_charge_expires_before_a_different_opponents_turn():
    from dominion.game.player_state import PlayerState

    state, player, source = new_state("Smithy")
    state.players.extend([PlayerState(ChooseFirstActionAI()), PlayerState(ChooseFirstActionAI())])
    state.current_player_index = 1
    daimyo, smithy = get_card("Daimyo"), get_card("Smithy")
    player.in_play = [daimyo, smithy]
    state.play_action_as_owner_indirectly(player, daimyo)
    state.current_player_index = 2
    before = player.actions_played
    state.play_action_as_owner_indirectly(player, smithy)
    assert player.actions_played - before == 1
    assert player.daimyo_pending == 0

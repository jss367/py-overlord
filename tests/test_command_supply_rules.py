"""Command targets stay virtual while their physical owners retain effects."""

import copy

import pytest

from dominion.ai.genetic_ai import GeneticAI
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState
from dominion.projects.citadel import Citadel
from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule
from dominion.ways.horse import WayOfTheHorse
from dominion.ways.turtle import WayOfTheTurtle


def setup(command="Overlord", target="Caravan", opponents=0):
    strategy = EnhancedStrategy()
    strategy.action_priority = [PriorityRule(target)]
    strategy.overlord_target_priority = [PriorityRule(target)]
    strategy.captain_target_priority = [PriorityRule(target)]
    strategy.band_of_misfits_target_priority = [PriorityRule(target)]
    player = PlayerState(GeneticAI(strategy))
    players = [player] + [PlayerState(GeneticAI(EnhancedStrategy())) for _ in range(opponents)]
    state = GameState(players, supply={target: 10, "Province": 8, "Gold": 30, "Spoils": 15})
    state.phase = "action"
    state.log_callback = lambda *args: None
    player.deck = [get_card("Copper") for _ in range(40)]
    card = get_card(command)
    player.in_play = [card]
    return state, player, card


@pytest.mark.parametrize("plays", [1, 2, 3])
def test_captain_has_one_next_turn_instruction_per_play(plays):
    state, player, captain = setup("Captain", "Village")
    for _ in range(plays):
        state.play_action_indirectly(player, captain)
    assert player.duration == [captain] * plays
    assert len(player.hand) == plays
    state.handle_cleanup_phase()
    assert captain in player.in_play
    before = len(player.hand)
    state.do_duration_phase()
    assert len(player.hand) == before + plays
    assert captain not in player.duration
    assert not captain.duration_persistent
    state.do_duration_phase()
    assert len(player.hand) == before + plays
    state.handle_cleanup_phase()
    assert captain not in player.in_play
    assert sum(c is captain for c in player.all_cards()) == 1


@pytest.mark.parametrize("empty_first,empty_next", [(True, False), (False, True), (True, True)])
def test_captain_finishes_even_with_empty_target_menus(empty_first, empty_next):
    state, player, captain = setup("Captain", "Village")
    state.supply["Village"] = 0 if empty_first else 10
    state.play_action_indirectly(player, captain)
    assert captain in player.duration
    before = len(player.hand)
    state.supply["Village"] = 0 if empty_next else 10
    state.do_duration_phase()
    assert len(player.hand) == before + (not empty_next)
    assert captain not in player.duration


def test_captain_instructions_survive_owner_self_movement():
    state, player, captain = setup("Captain", "Village")
    state.play_action_indirectly(player, captain)
    player.in_play.remove(captain)
    state.trash_card(player, captain)
    state.do_duration_phase()
    assert len(player.hand) == 2
    assert captain in state.trash
    assert captain not in player.all_cards()
    assert captain not in player.in_play


@pytest.mark.parametrize("command", ["Overlord", "Band of Misfits"])
@pytest.mark.parametrize("plays", [1, 2])
def test_virtual_duration_retains_command_then_releases_it(command, plays):
    state, player, owner = setup(command)
    owned_before = len(player.all_cards())
    for _ in range(plays):
        state.play_action_indirectly(player, owner)
    assert len(player.duration) == plays
    assert len(owner.duration_targets) == plays
    assert len(player.all_cards()) == owned_before
    assert player.count("Caravan") == 0
    assert state.supply["Caravan"] == 10
    state.handle_cleanup_phase()
    assert owner in player.in_play
    before = len(player.hand)
    state.do_duration_phase()
    assert len(player.hand) == before + plays
    assert player.duration == []
    assert all(c.name != "Caravan" for c in player.in_play)
    state.handle_cleanup_phase()
    assert owner not in player.in_play
    assert owner.duration_targets == []
    assert len(player.all_cards()) == owned_before


@pytest.mark.parametrize("command", ["Overlord", "Band of Misfits"])
def test_multiple_virtual_duration_targets_finish_independently(command):
    state, player, owner = setup(command)
    state.play_action_indirectly(player, owner)
    state.supply["Caravan"] = 0
    state.supply["Fishing Village"] = 10
    state.play_action_indirectly(player, owner)
    assert {c.name for c in owner.duration_targets} == {"Caravan", "Fishing Village"}
    state.handle_cleanup_phase()
    assert owner in player.in_play
    before = (len(player.hand), player.actions, player.coins)
    state.do_duration_phase()
    assert (len(player.hand), player.actions, player.coins) == (before[0] + 1, before[1] + 1, before[2] + 1)
    assert all(c.name not in {"Caravan", "Fishing Village"} for c in player.all_cards())
    state.handle_cleanup_phase()
    assert owner not in player.in_play


@pytest.mark.parametrize("command", ["Overlord", "Band of Misfits"])
def test_virtual_storage_counts_real_cards_without_owning_proxy(command):
    state, player, owner = setup(command, "Gear")
    player.ai.choose_gear_set_aside = lambda s, p, choices: choices[:2]
    owned_before = len(player.all_cards())
    state.play_action_indirectly(player, owner)
    saved = list(player.duration[0].set_aside)
    assert len(saved) == 2
    assert len(player.all_cards()) == owned_before
    assert player.count("Gear") == 0
    state.handle_cleanup_phase()
    state.do_duration_phase()
    assert all(c in player.hand for c in saved)
    assert all(c.name != "Gear" for c in player.in_play)
    assert len(player.all_cards()) == owned_before


@pytest.mark.parametrize("command", ["Overlord", "Band of Misfits", "Captain"])
def test_nested_virtual_multiplier_retains_command_and_physical_multiplier(command):
    state, player, owner = setup(command, "Throne Room")
    physical_throne = get_card("Throne Room")
    caravan = get_card("Caravan")
    player.hand = [physical_throne, caravan]
    state.play_action_indirectly(player, owner)
    assert player.duration.count(caravan) == 2
    assert caravan in owner.duration_targets
    assert physical_throne.duration_targets == [caravan]
    assert len([c for c in player.all_cards() if c.name == "Throne Room"]) == 1
    state.handle_cleanup_phase()
    assert {owner, physical_throne, caravan} <= set(player.in_play)
    before = len(player.hand)
    # Do not select another multiplier for Captain's next-turn instruction.
    state.supply["Throne Room"] = 0
    state.do_duration_phase()
    assert len(player.hand) == before + 2
    state.handle_cleanup_phase()
    assert all(c not in player.in_play for c in [owner, physical_throne, caravan])


@pytest.mark.parametrize("command", ["Overlord", "Band of Misfits", "Captain"])
def test_physical_throne_retains_command_playing_virtual_duration(command):
    state, player, owner = setup(command, "Village" if command == "Captain" else "Caravan")
    throne = get_card("Throne Room")
    player.hand = [owner]
    player.in_play = [throne]
    player.ai.strategy.action_priority = [PriorityRule(command)]
    state.play_action_indirectly(player, throne)
    assert throne.duration_targets == [owner]
    state.handle_cleanup_phase()
    assert throne in player.in_play and owner in player.in_play
    state.do_duration_phase()
    state.handle_cleanup_phase()
    assert throne not in player.in_play and owner not in player.in_play


@pytest.mark.parametrize("command", ["Overlord", "Band of Misfits", "Captain"])
def test_virtual_pillage_neither_attacks_nor_gains_spoils(command):
    state, player, owner = setup(command, "Pillage", opponents=1)
    player.cost_reduction = 1
    victim = state.players[1]
    victim.hand = [get_card("Copper") for _ in range(5)]
    seen = []
    player.ai.choose_card_to_discard_for_pillage = lambda *args: seen.append(args)
    state.play_action_indirectly(player, owner)
    assert seen == []
    assert len(victim.hand) == 5
    assert player.count("Spoils") == 0
    assert state.supply["Pillage"] == 10
    assert owner in player.in_play


@pytest.mark.parametrize("gain", [False, True])
def test_virtual_multiplier_tracks_a_duration_scheduled_by_a_later_gain(gain):
    state, player, owner = setup("Overlord", "Throne Room")
    cargo = get_card("Cargo Ship")
    player.hand = [cargo]
    player.ai.should_set_aside_cargo_ship = lambda s, p, c: True
    state.play_action_indirectly(player, owner)
    assert owner.duration_targets == [cargo]
    if gain:
        gold = state.gain_from_supply(player, "Gold")
        assert gold in player.all_cards()
    state.handle_cleanup_phase()
    assert (owner in player.in_play) is gain
    if gain:
        state.do_duration_phase()
        assert gold in player.hand
        state.handle_cleanup_phase()
        assert owner not in player.in_play


def test_virtual_duration_and_owner_references_survive_clone():
    state, player, owner = setup()
    state.play_action_indirectly(player, owner)
    clone = copy.deepcopy(state)
    cloned_player = clone.players[0]
    cloned_owner = cloned_player.in_play[0]
    assert cloned_owner.duration_targets[0] is cloned_player.duration[0]
    assert cloned_player.count("Caravan") == 0
    clone.do_duration_phase()
    assert cloned_player.duration == []
    assert player.duration != []


@pytest.mark.parametrize("command", ["Overlord", "Band of Misfits"])
@pytest.mark.parametrize("gain", [False, True])
def test_virtual_cargo_ship_registers_gain_and_retains_only_pending_return(command, gain):
    state, player, owner = setup(command, "Cargo Ship")
    player.ai.should_set_aside_cargo_ship = lambda s, p, c: True
    owned_before = len(player.all_cards())
    state.play_action_indirectly(player, owner)
    assert len(player.virtual_gain_effects) == 1
    if gain:
        gold = state.gain_from_supply(player, "Gold")
        assert gold not in player.discard
        assert gold in player.all_cards()
        assert player.count("Cargo Ship") == 0
        assert player.count("Gold") == 1
    state.supply["Cargo Ship"] = 0
    state.handle_cleanup_phase()
    assert not player.virtual_gain_effects
    assert (owner in player.in_play) is gain
    state.do_duration_phase()
    if gain:
        assert gold in player.hand
    assert len(player.all_cards()) == owned_before + gain
    state.handle_cleanup_phase()
    assert owner not in player.in_play


def test_virtual_recurring_duration_keeps_owner_until_last_instruction():
    state, player, owner = setup("Overlord", "Hireling")
    player.cost_reduction = 1
    state.play_action_indirectly(player, owner)
    proxy = player.duration[0]
    for _ in range(3):
        state.handle_cleanup_phase()
        assert owner in player.in_play
        state.do_duration_phase()
        assert player.duration == [proxy]
        assert player.count("Hireling") == 0
        assert all(c is not proxy for c in player.in_play)


def test_captain_next_turn_multiplier_can_schedule_a_later_duration():
    state, player, captain = setup("Captain", "Village")
    state.play_action_indirectly(player, captain)
    state.handle_cleanup_phase()
    caravan = get_card("Caravan")
    player.hand = [caravan]
    state.supply["Village"] = 0
    state.supply["Throne Room"] = 10
    state.do_duration_phase()
    assert player.duration == [caravan, caravan]
    assert captain not in player.duration
    assert captain.duration_targets == [caravan]
    state.handle_cleanup_phase()
    assert captain in player.in_play
    before = len(player.hand)
    state.do_duration_phase()
    assert len(player.hand) == before + 2
    state.handle_cleanup_phase()
    assert captain not in player.in_play


def test_virtual_duration_instruction_survives_trashed_command_without_ownership():
    state, player, owner = setup()
    state.play_action_indirectly(player, owner)
    player.in_play.remove(owner)
    state.trash_card(player, owner)
    before = len(player.hand)
    state.do_duration_phase()
    assert len(player.hand) == before + 1
    assert player.duration == []
    assert owner in state.trash
    assert owner not in player.in_play
    assert player.count("Caravan") == 0


def test_virtual_crew_never_moves_itself_on_duration():
    state, player, owner = setup("Overlord", "Crew")
    state.play_action_indirectly(player, owner)
    state.handle_cleanup_phase()
    state.do_duration_phase()
    assert player.count("Crew") == 0
    assert all(c.name != "Crew" for c in player.deck)
    state.handle_cleanup_phase()
    assert owner not in player.in_play


def test_virtual_blockade_keeps_real_storage_but_has_no_while_in_play_attack():
    state, player, owner = setup("Overlord", "Blockade", opponents=1)
    state.supply["Curse"] = 10
    player.ai.choose_card_to_gain_with_blockade = lambda s, p, max_cost: get_card("Blockade")
    state.play_action_indirectly(player, owner)
    assert player.count("Blockade") == 1  # The real gain, excluding the proxy.
    state.gain_from_supply(state.players[1], "Blockade")
    assert state.players[1].count("Curse") == 0
    state.handle_cleanup_phase()
    state.current_player_index = 0
    state.do_duration_phase()
    assert len([c for c in player.hand if c.name == "Blockade"]) == 1
    assert all(c.name != "Blockade" for c in player.in_play)


@pytest.mark.parametrize("target", ["Mining Village", "Encampment"])
@pytest.mark.parametrize("command", ["Overlord", "Band of Misfits", "Captain"])
def test_virtual_target_cannot_move_itself(command, target):
    state, player, owner = setup(command, target)
    player.ai.should_trash_mining_village = lambda s, p: True
    state.play_action_indirectly(player, owner)
    assert player.coins == (2 if target == "Encampment" else 0)
    assert state.supply[target] == 10
    assert state.trash == []
    assert all(c.name != target for c in player.all_cards())


@pytest.mark.parametrize("way_class", [WayOfTheHorse, WayOfTheTurtle])
@pytest.mark.parametrize("command", ["Overlord", "Band of Misfits", "Captain"])
def test_moving_ways_leave_supply_proxy_virtual(command, way_class):
    state, player, owner = setup(command, "Village")
    way = way_class()
    state.ways = [way]
    offers = []
    player.ai.strategy.choose_way = lambda s, p, c, choices: offers.append(c.name) or (way if c.name == "Village" else None)
    state.play_action_indirectly(player, owner)
    assert offers == [command, "Village"]
    assert player.actions_played == 2
    assert state.supply["Village"] == 10
    assert not getattr(player, "turtle_set_aside", [])
    assert all(c.name != "Village" for c in player.all_cards())


@pytest.mark.parametrize("command", ["Overlord", "Band of Misfits", "Captain"])
def test_supply_plays_fire_shared_hooks_once_per_play(command):
    state, player, owner = setup(command, "Village")
    seen = []
    state.fire_prophecy_action_hooks = lambda p, c: seen.append(("prophecy", c.name))
    state.fire_ally_play_hooks = lambda p, c: seen.append(("ally", c.name))
    state._call_tavern_triggers = lambda p, event, c=None: seen.append(("tavern", c.name))
    state.play_action_indirectly(player, owner)
    assert len(seen) == 6
    for hook in ["prophecy", "ally", "tavern"]:
        assert seen.count((hook, command)) == seen.count((hook, "Village")) == 1


@pytest.mark.parametrize("command", ["Overlord", "Band of Misfits", "Captain"])
def test_citadel_replays_outer_command_not_its_first_nested_target(command):
    state, player, owner = setup(command, "Village")
    player.projects = [Citadel()]
    state.play_action_indirectly(player, owner)
    assert player.actions_played == 4
    assert len(player.hand) == 2
    if command == "Captain":
        assert player.duration == [owner, owner]


@pytest.mark.parametrize("command", ["Overlord", "Band of Misfits", "Captain"])
def test_virtual_feast_still_gains_without_self_trash(command):
    state, player, owner = setup(command, "Feast")
    state.supply["Silver"] = 40
    player.ai.strategy.gain_priority = [PriorityRule("Silver")]
    state.play_action_indirectly(player, owner)
    assert len(player.discard) == 1
    assert player.discard[0].name == "Silver"
    assert state.trash == []
    assert state.supply["Feast"] == 10


@pytest.mark.parametrize("spoils", [0, 1, 2])
def test_pillage_attack_precedes_spoils_and_cannot_repeat_after_trash(spoils):
    state, attacker, pillage = setup("Pillage", "Village", opponents=2)
    state.current_player_index = 1
    attacker = state.players[1]
    attacker.in_play = [pillage]
    state.players[0].in_play = []
    state.supply["Spoils"] = spoils
    for player in [state.players[2], state.players[0]]:
        player.hand = [get_card("Copper") for _ in range(5)]
    seen = []
    def discard_choice(s, a, victim, choices):
        assert pillage in s.trash
        assert a.count("Spoils") == 0
        seen.append(victim)
        return choices[0]
    attacker.ai.choose_card_to_discard_for_pillage = discard_choice
    state.play_action_indirectly(attacker, pillage)
    assert seen == [state.players[2], state.players[0]]
    assert attacker.count("Spoils") == spoils
    state.play_action_indirectly(attacker, pillage)
    assert len(seen) == 2
    assert attacker.count("Spoils") == spoils


@pytest.mark.parametrize("command", ["Overlord", "Band of Misfits"])
@pytest.mark.parametrize("gain_source", ["hand", "play_before", "play_after", "discard_hook"])
@pytest.mark.parametrize("multiplied", [False, True])
def test_cleanup_gain_retains_virtual_cargo_ship_owner(command, gain_source, multiplied):
    state, player, owner = setup(command, "Cargo Ship")
    player.ai.should_set_aside_cargo_ship = lambda s, p, c: True
    throne = get_card("Throne Room")
    if multiplied:
        player.hand = [owner]
        player.in_play = [throne]
        player.ai.strategy.action_priority = [PriorityRule(command)]
        state.play_action_indirectly(player, throne)
    else:
        state.play_action_indirectly(player, owner)
    friendly = get_card("Gold")
    state.pile_traits["Gold"] = "Friendly"
    if gain_source == "hand":
        player.hand = [friendly]
    elif gain_source == "play_before":
        player.in_play.insert(0, friendly)
    else:
        player.in_play.append(friendly)
        if gain_source == "discard_hook":
            friendly.on_discard_from_play = lambda s, p: s.gain_from_supply(p, "Gold")
    state.handle_cleanup_phase()
    assert owner in player.in_play
    if multiplied:
        assert throne in player.in_play
        assert throne.duration_targets == [owner]
    cargos = [c for c in player.duration if c.name == "Cargo Ship"]
    assert cargos and all(c.set_aside is not None for c in cargos)
    stored = [c.set_aside for c in cargos]
    assert all(c in player.all_cards() for c in stored)
    assert player.count("Cargo Ship") == 0
    state.do_duration_phase()
    assert all(c in player.hand for c in stored)
    state.handle_cleanup_phase()
    assert owner not in player.in_play
    assert owner.duration_targets == []
    if multiplied:
        assert throne not in player.in_play
        assert throne.duration_targets == []

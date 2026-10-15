"""Physical storage, independent attacks and one-shot returns for Blockade replays."""

import copy
from collections import Counter

import pytest

from dominion.cards.registry import get_card
from tests.test_named_card_decisions import make_state


def choose_gains(player, names):
    choices = iter(names)
    player.ai.choose_card_to_gain_with_blockade = lambda *_a, **_k: get_card(next(choices))


def play_repeatedly(state, player, names):
    blockade = get_card("Blockade")
    player.in_play = [blockade]
    choose_gains(player, names)
    for _ in names:
        state.play_action_indirectly(player, blockade)
    return blockade


@pytest.mark.parametrize("multiplier,names", [
    ("Throne Room", ("Silver", "Silver")),
    ("Throne Room", ("Estate", "Estate")),
    ("Throne Room", ("Silver", "Village")),
    ("King's Court", ("Silver", "Village", "Silver")),
])
def test_multiplier_preserves_every_card_attack_and_single_return(multiplier, names):
    state, player = make_state(kingdom=("Blockade", "Village", multiplier))
    blockade, command = get_card("Blockade"), get_card(multiplier)
    player.hand, player.in_play = [blockade], [command]
    player.ai.choose_action = lambda _s, choices: blockade if blockade in choices else None
    choose_gains(player, names)
    supply_before = dict(state.supply)
    state.play_action_indirectly(player, command)
    stored = blockade.set_aside
    assert [c.name for c in stored] == list(names)
    assert len({id(c) for c in stored}) == len(names)
    assert player.duration == [blockade] * len(names)
    for name, count in Counter(names).items():
        assert state.supply[name] == supply_before[name] - count
        assert player.count(name) == count
    assert player.get_victory_points(state) == names.count("Estate")
    assert {blockade, command} <= state._cards_retained_in_play(player)

    menus = []
    def choose_effect(_s, _p, _gain, choices):
        menus.append([e for e in choices if e.source is blockade])
        return choices[0]
    player.ai.strategy.choose_gain_effect = choose_effect
    state.current_player_index = 1
    victim = state.players[1]
    for name in dict.fromkeys(names):
        curses_before = victim.count("Curse")
        state.gain_from_supply(victim, name)
        assert victim.count("Curse") == curses_before + names.count(name)
    if names.count("Silver") > 1:
        assert max(map(len, menus)) == names.count("Silver")
    # A later gain triggers the same stored cards again, once each.
    curses_before = victim.count("Curse")
    state.gain_from_supply(victim, "Silver")
    assert victim.count("Curse") == curses_before + names.count("Silver")

    state.current_player_index = 0
    state.handle_cleanup_phase()
    assert blockade in player.in_play and command in player.in_play
    state.handle_cleanup_phase()  # Opponent's turn ends.
    state.do_duration_phase()
    assert not blockade.set_aside and not player.duration
    assert all(sum(c is stored_card for c in player.hand) == 1 for stored_card in stored)
    assert player.hand == stored
    assert player.get_victory_points(state) == names.count("Estate")
    state.current_player_index = 1
    curses_before = victim.count("Curse")
    for name in dict.fromkeys(names):
        state.gain_from_supply(victim, name)
    assert victim.count("Curse") == curses_before
    state.current_player_index = 0
    state.do_duration_phase()  # Completed instructions never return them twice.
    assert player.hand == stored
    state.handle_cleanup_phase()
    assert blockade not in player.in_play and command not in player.in_play
    assert sum(c is blockade for c in player.all_cards()) == 1
    assert sum(c is command for c in player.all_cards()) == 1


def test_each_play_keeps_its_own_immunity_snapshot_and_survives_deepcopy():
    state, player = make_state(kingdom=("Blockade", "Lighthouse"), players=3)
    first, second = state.players[1:]
    blockade = get_card("Blockade")
    player.in_play = [blockade]
    choose_gains(player, ("Silver",) * 3)
    first.duration = [get_card("Lighthouse")]
    state.play_action_indirectly(player, blockade)
    first.duration, second.duration = [], [get_card("Lighthouse")]
    state.play_action_indirectly(player, blockade)
    second.duration = []
    state.play_action_indirectly(player, blockade)
    clone = copy.deepcopy(state)
    for game in (state, clone):
        game.current_player_index = 1
        game.gain_from_supply(game.players[1], "Silver")
        assert game.players[1].count("Curse") == 2
        game.gain_from_supply(game.players[2], "Silver")  # Off-turn gain.
        assert game.players[2].count("Curse") == 0
        game.current_player_index = 2
        game.gain_from_supply(game.players[2], "Silver")
        assert game.players[2].count("Curse") == 2
    assert clone.players[0].count("Silver") == player.count("Silver") == 3
    assert all(c is not original for c, original in zip(clone.players[0].all_cards(), player.all_cards()))


@pytest.mark.parametrize("failure_first", [False, True])
@pytest.mark.parametrize("reaction", ["trader", "trash", "topdeck"])
def test_failed_storage_does_not_replace_or_consume_successful_play_returns(failure_first, reaction):
    state, player = make_state(kingdom=("Blockade", "Village", "Smithy", "Trader", "Watchtower"))
    player.hand = [get_card("Trader" if reaction == "trader" else "Watchtower")]
    player.ai.strategy.should_reveal_trader = lambda _s, _p, card, **_k: card.name == "Smithy"
    player.ai.strategy.choose_watchtower_reaction = lambda _s, _p, card: reaction if card.name == "Smithy" else None
    names = ("Smithy", "Silver", "Village") if failure_first else ("Silver", "Village", "Smithy")
    blockade = play_repeatedly(state, player, names)
    stored = blockade.set_aside
    assert [c.name for c in stored] == ["Silver", "Village"]
    assert player.duration == [blockade, blockade]
    state.current_player_index = 1
    for name in ("Silver", "Village", "Smithy"):
        state.gain_from_supply(state.players[1], name)
    assert state.players[1].count("Curse") == 2
    state.current_player_index = 0
    state.do_duration_phase()
    assert not player.duration and not blockade.set_aside
    assert all(sum(card is c for card in player.hand) == 1 for c in stored)


def test_stored_cards_and_watches_survive_the_physical_blockade_being_trashed():
    state, player = make_state(kingdom=("Blockade", "Village"))
    blockade = play_repeatedly(state, player, ("Silver", "Village"))
    stored = blockade.set_aside
    player.in_play.remove(blockade)
    state.trash_card(player, blockade)
    assert all(c in player.all_cards() for c in stored)
    assert blockade not in player.all_cards()
    state.current_player_index = 1
    for name in ("Silver", "Village"):
        state.gain_from_supply(state.players[1], name)
    assert state.players[1].count("Curse") == 2
    state.current_player_index = 0
    state.do_duration_phase()
    assert player.hand == stored
    assert blockade in state.trash and blockade not in player.in_play
    assert not player.duration


def test_repeated_command_plays_keep_virtual_stores_and_release_multiplier_chain():
    state, player = make_state(kingdom=("Blockade", "Village", "Throne Room", "Overlord"))
    throne, overlord = get_card("Throne Room"), get_card("Overlord")
    player.in_play, player.hand = [throne], [overlord]
    player.ai.choose_action = lambda _s, choices: overlord if overlord in choices else None
    player.ai.choose_overlord_target = lambda *_a, **_k: get_card("Blockade")
    choose_gains(player, ("Silver", "Village"))
    state.play_action_indirectly(player, throne)
    proxies = list(player.duration)
    assert len(proxies) == 2 and all(c.virtual_supply_play for c in proxies)
    assert proxies[0] is not proxies[1]
    assert player.count("Blockade") == 0
    assert player.count("Silver") == player.count("Village") == 1
    assert {throne, overlord} <= state._cards_retained_in_play(player)
    state.current_player_index = 1
    for name in ("Silver", "Village"):
        state.gain_from_supply(state.players[1], name)
    assert state.players[1].count("Curse") == 2
    state.current_player_index = 0
    state.handle_cleanup_phase()
    state.handle_cleanup_phase()
    state.do_duration_phase()
    assert sorted(c.name for c in player.hand) == ["Silver", "Village"]
    assert not player.duration and player.count("Blockade") == 0
    state.handle_cleanup_phase()
    assert throne not in player.in_play and overlord not in player.in_play


@pytest.mark.parametrize("curses", [0, 1, 3])
def test_multiple_watches_respect_the_remaining_curse_pile(curses):
    state, player = make_state(kingdom=("Blockade",))
    play_repeatedly(state, player, ("Silver", "Silver"))
    state.supply["Curse"] = curses
    state.current_player_index = 1
    state.gain_from_supply(state.players[1], "Silver")
    assert state.players[1].count("Curse") == min(curses, 2)
    assert state.supply["Curse"] == max(curses - 2, 0)


def test_each_return_expires_only_its_own_stored_card_watch():
    state, player = make_state(kingdom=("Blockade",))
    blockade = play_repeatedly(state, player, ("Silver", "Silver"))
    first, second = blockade.set_aside
    player.duration.remove(blockade)  # Consume the first scheduled callback.
    blockade.on_duration(state)
    assert player.hand == [first] and blockade.set_aside == [second]
    state.current_player_index = 1
    state.gain_from_supply(state.players[1], "Silver")
    assert state.players[1].count("Curse") == 1
    state.current_player_index = 0
    player.duration.remove(blockade)
    blockade.on_duration(state)
    assert player.hand == [first, second] and not blockade.set_aside
    state.current_player_index = 1
    state.gain_from_supply(state.players[1], "Silver")
    assert state.players[1].count("Curse") == 1


def test_legacy_opponent_gain_dispatch_also_resolves_each_play_once():
    state, player = make_state(kingdom=("Blockade",))
    play_repeatedly(state, player, ("Silver", "Silver"))
    state.current_player_index = 1
    victim = state.players[1]
    gained = state.take_top_supply_card("Silver")
    victim.discard.append(gained)
    state._handle_opponent_gain_hooks(victim, gained)
    assert victim.count("Curse") == 2


@pytest.mark.parametrize("location", ["virtual", "trash"])
def test_other_durations_see_stored_ownership_before_blockade_returns(location):
    state, player = make_state(kingdom=("Blockade", "Village", "Cobbler", "Overlord"))
    cobbler = get_card("Cobbler")
    player.in_play = [cobbler]
    cobbler.on_play(state)
    if location == "trash":
        blockade = play_repeatedly(state, player, ("Silver", "Village"))
        player.in_play.remove(blockade)
        state.trash_card(player, blockade)
    else:
        overlord = get_card("Overlord")
        player.in_play = [overlord]
        player.ai.choose_overlord_target = lambda *_a, **_k: get_card("Blockade")
        choose_gains(player, ("Silver", "Village"))
        for _ in range(2):
            state.play_action_indirectly(player, overlord)
    assert player.duration[0] is cobbler
    observed = []
    def choose(_s, owner, choices, _limit):
        observed.append((owner.count("Silver"), owner.count("Village")))
        assert observed[-1] == (1, 1)
        return next(c for c in choices if c.name == "Copper")
    player.ai.choose_card_to_gain_to_hand = choose
    state.do_duration_phase()
    assert observed == [(1, 1)]
    assert not player._resolving_duration_sources
    assert sorted(c.name for c in player.hand) == ["Copper", "Silver", "Village"]
    assert not player.duration

"""Seeded conservation checks across replay, cleanup, and ownership boundaries."""

from collections import Counter
import copy
import random

import pytest

from dominion.ai.genetic_ai import GeneticAI
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState
from dominion.strategy.enhanced_strategy import EnhancedStrategy
from tests.card_conservation import CardConservation, inventory

SEEDS = [17, 101, 1729, 4242]


def make_state(players=2):
    owners = [PlayerState(GeneticAI(EnhancedStrategy())) for _ in range(players)]
    state = GameState(owners, supply={
        "Province": 8, "Estate": 12, "Curse": 30, "Copper": 60, "Silver": 40,
        "Gold": 30, "Village": 10, "Smithy": 10, "Gear": 10, "Haven": 10,
        "Blockade": 10, "Throne Room": 10, "Overlord": 10, "Band of Misfits": 10,
        "Lurker": 10, "Courier": 10,
    })
    state.phase = "action"
    state.log_callback = lambda *_: None
    return state


def owned_ids(player):
    return Counter(id(card) for card in player.all_cards())


@pytest.mark.parametrize("corruption,match", [
    ("lost", r"missing=\{'Gold': 1\}, extra=\{\}"),
    ("extra", r"missing=\{\}, extra=\{'Gold': 1\}"),
    ("duplicate", "multiple physical zones"),
    ("second_owner", "multiple physical zones"),
    ("negative_supply", "negative Supply count"),
    ("virtual_physical", "virtual card"),
])
def test_checker_rejects_corruption_and_identifies_the_failing_transition(corruption, match):
    state = make_state()
    player, other = state.players
    card = get_card("Gold")
    player.hand = [card]
    conservation = CardConservation(state, seed=1729)
    with pytest.raises(AssertionError, match=match) as failure:
        with conservation.step(state, "deliberate corruption"):
            if corruption == "lost":
                player.hand.clear()
            elif corruption == "extra":
                player.hand.append(get_card("Gold"))
            elif corruption == "duplicate":
                player.deck.append(card)
                assert len(player.all_cards()) == 1  # Ownership deduplication hides this error.
            elif corruption == "second_owner":
                other.hand.append(card)
            elif corruption == "negative_supply":
                state.supply["Gold"] = -1
            else:
                card.virtual_supply_play = True
    assert any("seed=1729; step=deliberate corruption; phase=action; turn=1; player=0" in note
               for note in failure.value.__notes__)


def test_checker_counts_ordered_pile_members_and_rejects_mismatched_counts():
    state = make_state()
    state.supply["Knights"] = 2
    state.pile_order["Knights"] = ["Dame Anna", "Sir Martin"]
    conservation = CardConservation(state, seed=17)
    assert "Knights" not in conservation.expected
    assert conservation.expected["Dame Anna"] == conservation.expected["Sir Martin"] == 1
    with conservation.step(state, "gain exposed Knight"):
        assert state.gain_from_supply(state.players[0], "Sir Martin").name == "Sir Martin"
    state.supply["Knights"] = 2
    with pytest.raises(AssertionError, match="pile accounting mismatch"):
        conservation.check(state, "corrupt ordered pile count")


def test_pending_references_do_not_duplicate_physical_sources_or_their_storage():
    state = make_state()
    first, second = state.players
    source, stored = get_card("Gear"), get_card("Gold")
    source.set_aside = [stored]
    first.in_play = [source]
    first.duration = [source, source]
    first.multiplied_durations = [source]
    counts = inventory(state)
    assert counts["Gear"] == state.supply["Gear"] + 1
    assert counts["Gold"] == state.supply["Gold"] + 1
    # A legacy queue can be the source's only location, still once per copy.
    first.in_play.clear()
    assert inventory(state) == counts
    # A moved source remains an instruction reference for its previous owner.
    source.set_aside = []
    first.hand = [stored]
    second.in_play = [source]
    assert inventory(state) == counts


def observe_returns(source, saved, conservation, returns):
    """Inspect each callback while its queue entries are temporarily removed."""
    original = source.on_duration
    saved_ids = {id(card) for card in saved}

    def on_duration(game):
        before = Counter(id(card) for card in game.current_player.hand)
        original(game)
        after = Counter(id(card) for card in game.current_player.hand)
        returns.update({card_id: n for card_id, n in (after - before).items() if card_id in saved_ids})
        conservation.check(game, "individual Duration instruction")

    source.on_duration = on_duration


@pytest.mark.parametrize("seed_rng", SEEDS, indirect=True)
@pytest.mark.parametrize("target_name", ["Haven", "Gear"])
@pytest.mark.parametrize("command_name", [None, "Overlord", "Band of Misfits"],
                         ids=["physical-duration", "overlord", "band-of-misfits"])
def test_replayed_storage_conserves_cards_through_each_turn_boundary(seed_rng, target_name, command_name):
    rng = random.Random(seed_rng)
    state = make_state()
    player, opponent = state.players
    throne, source = get_card("Throne Room"), get_card(command_name or target_name)
    player.hand = [throne, source, get_card("Gold"), get_card("Silver"), get_card("Estate")]
    player.deck = [get_card(name) for name in ["Copper", "Silver", "Gold", "Estate", "Village", "Smithy"] * 3]
    rng.shuffle(player.deck)
    player.ai.choose_action = lambda _s, choices: source if source in choices else None
    player.ai.choose_gear_set_aside = lambda _s, _p, choices: rng.sample(choices, min(rng.randint(1, 2), len(choices)))
    player.ai.choose_card_to_set_aside_for_haven = lambda _s, _p, choices: rng.choice(choices)
    if command_name:
        hook = "choose_overlord_target" if command_name == "Overlord" else "choose_band_of_misfits_target"
        setattr(player.ai, hook, lambda *_a, **_k: get_card(target_name))
    conservation = CardConservation(state, seed=seed_rng)
    expected_owned = Counter(id(card) for card in player.hand + player.deck)
    target_supply = state.supply[target_name]

    with conservation.step(state, "Throne Room plays its target twice"):
        assert state.play_action_from_hand_indirectly(player, throne)
        assert len(player.duration) == 2
        instructions = list(dict.fromkeys(player.duration))
        saved = [card for instruction in instructions for card in instruction.set_aside]
        assert len(saved) >= 2
        assert len({id(card) for card in saved}) == len(saved)
        assert owned_ids(player) == expected_owned
        assert not owned_ids(opponent)
        assert state.supply[target_name] == target_supply
        if command_name:
            assert len(instructions) == 2
            assert all(card.virtual_supply_play for card in instructions)
            assert player.count(target_name) == 0
        else:
            assert instructions == [source]

    returns = Counter()
    for instruction in instructions:
        observe_returns(instruction, saved, conservation, returns)
    for label in ("owner cleanup", "opponent cleanup"):
        with conservation.step(state, label):
            state.handle_cleanup_phase()
            assert throne in player.in_play and source in player.in_play
            assert all(card not in player.hand for card in saved)
            assert owned_ids(player) == expected_owned
    assert state.current_player is player
    with conservation.step(state, "owner's next start phase"):
        state.handle_start_phase()
        assert not player.duration
        assert all(not instruction.set_aside for instruction in instructions)
        assert all(sum(card is held for held in player.hand) == 1 for card in saved)
        assert returns == Counter({id(card): 1 for card in saved})
        assert owned_ids(player) == expected_owned
    with conservation.step(state, "repeat Duration resolution has no effect"):
        hand = list(player.hand)
        state.do_duration_phase()
        assert player.hand == hand
        assert returns == Counter({id(card): 1 for card in saved})
    with conservation.step(state, "completed multiplier and source leave play"):
        state.handle_cleanup_phase()
        assert throne not in player.in_play and source not in player.in_play
        assert owned_ids(player) == expected_owned


@pytest.mark.parametrize("seed_rng", SEEDS, indirect=True)
@pytest.mark.parametrize("return_order", [(0, 1), (1, 0)], ids=["old-owner-first", "new-owner-first"])
@pytest.mark.parametrize("clone", [False, True], ids=["original", "deepcopy"])
def test_transferred_blockade_preserves_each_owners_cards_and_single_returns(seed_rng, return_order, clone):
    rng = random.Random(seed_rng)
    state = make_state(players=3)
    first, second, victim = state.players
    blockade, lurker, courier = (get_card(name) for name in ("Blockade", "Lurker", "Courier"))
    first.hand = [blockade]
    second.hand = [lurker, courier]
    names = [["Estate", rng.choice(["Silver", "Estate"])], ["Estate", rng.choice(["Village", "Silver"])]]
    for batch in names:
        rng.shuffle(batch)
    conservation = CardConservation(state, seed=seed_rng)

    def choose_gains(owner, batch):
        choices = iter(batch)
        owner.ai.choose_card_to_gain_with_blockade = lambda *_a, **_k: get_card(next(choices))

    choose_gains(first, names[0])
    for play in range(2):
        with conservation.step(state, f"old owner Blockade play {play}"):
            if play == 0:
                assert state.play_action_from_hand_indirectly(first, blockade)
            else:
                state.play_action_indirectly(first, blockade)
    first_stored = list(blockade.set_aside)
    with conservation.step(state, "source moves to trash while stored cards remain owned"):
        first.in_play.remove(blockade)
        state.trash_card(first, blockade)
        assert blockade not in first.all_cards()
        assert Counter(c.name for c in first.all_cards()) == Counter(names[0])
    with conservation.step(state, "old owner cleanup"):
        state.handle_cleanup_phase()
        assert state.current_player is second
    second.ai.choose_lurker_mode = lambda *_a, **_k: "gain"
    second.ai.choose_action_to_gain_from_trash = lambda *_a, **_k: blockade
    with conservation.step(state, "Lurker gains the same physical source from trash"):
        state.handle_start_phase()
        assert state.play_action_from_hand_indirectly(second, lurker)
        assert blockade in second.discard and blockade not in state.trash
    second.ai.choose_courier_target = lambda *_a, **_k: blockade
    choose_gains(second, names[1])
    with conservation.step(state, "Courier plays the transferred Blockade"):
        assert state.play_action_from_hand_indirectly(second, courier)
        assert blockade in second.in_play
    with conservation.step(state, "new owner repeats the source"):
        state.play_action_indirectly(second, blockade)
        assert first.duration == second.duration == [blockade, blockade]
    second_stored = [card for card in blockade.set_aside if card not in first_stored]
    if clone:
        memo = {}
        state = copy.deepcopy(state, memo)
        first_stored = [memo[id(card)] for card in first_stored]
        second_stored = [memo[id(card)] for card in second_stored]
        first, second, victim = state.players
        blockade = next(card for card in second.in_play if card.name == "Blockade")
        conservation.check(state, "deepcopy preserves inventories and owner references")
    stored = {0: first_stored, 1: second_stored}
    with conservation.step(state, "storage belongs to the player who made each play"):
        assert Counter(c.name for c in stored[0]) == Counter(names[0])
        assert Counter(c.name for c in stored[1]) == Counter(names[1])
        assert blockade.set_aside_for_owner(first) == stored[0]
        assert blockade.set_aside_for_owner(second) == stored[1]
        assert owned_ids(first) == Counter(id(c) for c in stored[0])
        # The old owner's watches can attack the new owner during these gains.
        expected_curses = sum(Counter(names[0])[name] for name in names[1])
        curses_received = [c for c in second.hand + second.deck + second.discard if c.name == "Curse"]
        assert len(curses_received) == expected_curses
        assert owned_ids(second) == Counter(id(c) for c in second.in_play + stored[1] + curses_received)
        assert not (set(owned_ids(first)) & set(owned_ids(second)))
    returns = Counter()
    observe_returns(blockade, stored[0] + stored[1], conservation, returns)
    curses = 0

    def victim_gains(label):
        nonlocal curses
        state.current_player_index = 2
        for name in sorted(set(names[0] + names[1])):
            matches = sum(play.card.name == name for play in blockade.pending_plays)
            with conservation.step(state, f"{label}: opponent gains {name}"):
                assert state.gain_from_supply(victim, name) is not None
                curses += matches
                assert victim.count("Curse") == curses

    victim_gains("both owners have pending instructions")
    for index in return_order:
        state.current_player_index = index
        with conservation.step(state, f"owner {index} resolves its own stored cards"):
            state.phase = "start"
            state.handle_start_phase()
            assert not state.players[index].duration
            assert all(sum(card is held for held in state.players[index].hand) == 1 for card in stored[index])
            other = 1 - index
            assert all(card not in state.players[other].all_cards() for card in stored[index])
        with conservation.step(state, f"owner {index} cannot receive the same cards twice"):
            hand = list(state.players[index].hand)
            state.do_duration_phase()
            assert state.players[index].hand == hand
        with conservation.step(state, f"owner {index} cleanup can move the physical source"):
            state.handle_cleanup_phase()
            assert sum(card is blockade for card in second.all_cards()) == 1
            assert blockade not in first.all_cards()
        victim_gains(f"after owner {index} returns")
    with conservation.step(state, "all records completed"):
        assert not blockade.pending_plays
        assert returns == Counter({id(card): 1 for batch in stored.values() for card in batch})
        assert all(card in first.all_cards() for card in stored[0])
        assert all(card in second.all_cards() for card in stored[1])

"""Strategy hooks through real plays, Duration queues, gains, and attacks."""
from types import SimpleNamespace

import pytest

from dominion.ai.genetic_ai import GeneticAI
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState
from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


def setup(strategy=None, names=(), opponents=0):
    players = [PlayerState(GeneticAI(strategy or EnhancedStrategy()))]
    players += [PlayerState(GeneticAI(EnhancedStrategy())) for _ in range(opponents)]
    state = GameState(players, supply={"Province": 8, "Curse": 10, "Silver": 40,
                                      "Gold": 30, "Horse": 30, "Smithy": 10})
    state.phase = "action"
    state.log_callback = lambda *args: None
    players[0].hand = [get_card(n) for n in names]
    return state, players[0]


def play(state, player, card):
    player.in_play.append(card)
    player.actions -= 1
    state.play_action_indirectly(player, card)


@pytest.mark.parametrize("now", [True, False])
def test_barge_override_runs_through_play_and_duration(now):
    seen = []
    strategy = EnhancedStrategy()
    strategy.should_resolve_barge_now = lambda s, p: seen.append((s, p)) or now
    state, player = setup(strategy)
    player.deck = [get_card("Copper") for _ in range(10)]
    barge = get_card("Barge")
    play(state, player, barge)
    assert seen == [(state, player)]
    assert len(player.hand) == (3 if now else 0)
    assert player.buys == (2 if now else 1)
    assert (barge in player.duration) is not now
    state.handle_cleanup_phase()
    assert (barge in player.in_play) is not now
    before = len(player.hand)
    state.do_duration_phase()
    assert len(player.hand) == before + (0 if now else 3)
    assert player.buys == (1 if now else 2)
    assert barge not in player.duration


@pytest.mark.parametrize("answers", [(False, False), (False, True), (True, False), (True, True)])
def test_barge_replays_preserve_every_timing_choice(answers):
    strategy = EnhancedStrategy()
    decisions = iter(answers)
    strategy.should_resolve_barge_now = lambda s, p: next(decisions)
    state, player = setup(strategy)
    player.deck = [get_card("Copper") for _ in range(12)]
    barge = get_card("Barge")
    play(state, player, barge)
    state.play_action_indirectly(player, barge)
    assert len(player.hand) == 3 * sum(answers)
    state.do_duration_phase()
    assert len(player.hand) == 6
    assert player.buys == 3
    assert barge not in player.duration
    state.do_duration_phase()
    assert len(player.hand) == 6


def test_barge_separate_copies_and_empty_draws():
    strategy = EnhancedStrategy()
    strategy.should_resolve_barge_now = lambda s, p: False
    state, player = setup(strategy)
    first, second = get_card("Barge"), get_card("Barge")
    play(state, player, first)
    play(state, player, second)
    state.do_duration_phase()
    assert player.hand == []
    assert player.buys == 3
    assert not player.duration


@pytest.mark.parametrize("answer", [None, "now", [], 1])
def test_barge_invalid_override_uses_fallback(answer):
    strategy = EnhancedStrategy()
    strategy.should_resolve_barge_now = lambda s, p: answer
    state, player = setup(strategy)
    player.deck = [get_card("Gold") for _ in range(4)]
    play(state, player, get_card("Barge"))
    assert len(player.hand) == 3


@pytest.mark.parametrize("names,deck,actions,phase,expected", [
    ((), ("Gold", "Gold", "Gold"), 1, "action", True),
    ((), ("Smithy", "Smithy", "Smithy"), 1, "action", False),
    ((), ("Smithy", "Smithy", "Smithy"), 2, "action", True),
    ((), (), 1, "action", False),
    ((), ("Gold",), 1, "buy", False),
])
def test_barge_fallback_context_without_strategy_hook(names, deck, actions, phase, expected):
    state, player = setup(SimpleNamespace(), names)
    state.phase = phase
    player.actions = actions
    player.deck = [get_card(n) for n in deck]
    barge = get_card("Barge")
    play(state, player, barge)
    assert (barge in player.duration) is not expected


def test_barge_final_province_prefers_now():
    state, player = setup(names=("Gold", "Gold", "Silver"))
    state.supply["Province"] = 1
    player.deck = [get_card("Smithy") for _ in range(3)]
    play(state, player, get_card("Barge"))
    assert len(player.hand) == 6
    assert not player.duration


@pytest.mark.parametrize("answer", [None, "hand", "deck", "invalid", [], {}])
@pytest.mark.parametrize("to_hand,to_deck", [(False, False), (True, False), (False, True)])
def test_sleigh_override_destinations_and_consumption(answer, to_hand, to_deck):
    seen = []
    strategy = EnhancedStrategy()
    strategy.choose_sleigh_reaction = lambda s, p, c: seen.append((s, p, c)) or answer
    state, player = setup(strategy, ("Sleigh",))
    sleigh = player.hand[0]
    gold = get_card("Gold")
    state.gain_card(player, gold, to_hand=to_hand, to_deck=to_deck)
    assert seen == [(state, player, gold)]
    reacted = answer in ("hand", "deck")
    assert (sleigh in player.discard) is reacted
    assert (sleigh in player.hand) is not reacted
    destination = player.hand if answer == "hand" else player.deck if answer == "deck" else (
        player.deck if to_deck else player.hand if to_hand else player.discard)
    assert gold in destination
    assert sum(c is gold for c in player.all_cards()) == 1


@pytest.mark.parametrize("gain,phase,actions,answer", [
    ("Gold", "action", 1, "hand"), ("Silver", "action", 1, None),
    ("Silver", "treasure", 0, "hand"), ("Gold", "buy", 0, "deck"),
    ("Smithy", "action", 0, "deck"), ("Smithy", "action", 1, "hand"),
    ("Curse", "action", 1, None), ("Copper", "buy", 0, None),
    ("Province", "buy", 0, None), ("Ghost Town", "buy", 0, None),
])
def test_sleigh_default_phase_and_reaction_cost(gain, phase, actions, answer):
    state, player = setup(SimpleNamespace(), ("Sleigh",))
    state.phase = phase
    player.actions = actions
    card = get_card(gain)
    state.gain_card(player, card)
    assert any(c.name == "Sleigh" for c in player.hand) is (answer is None)
    assert card in (player.hand if answer == "hand" or gain == "Ghost Town" else player.deck if answer == "deck" else player.discard)


def test_sleigh_off_turn_and_existing_destination():
    state, owner = setup(names=("Sleigh",), opponents=1)
    target = state.players[1]
    target.hand = [get_card("Sleigh")]
    gold = get_card("Gold")
    state.gain_card(target, gold)
    assert gold in target.deck
    gold = get_card("Gold")
    state.gain_card(owner, gold, to_hand=True)
    assert any(c.name == "Sleigh" for c in owner.hand)


def test_sleigh_and_sheepdog_use_the_redirected_gain():
    strategy = EnhancedStrategy()
    strategy.choose_sleigh_reaction = lambda s, p, c: "deck"
    state, player = setup(strategy, ("Sleigh", "Sheepdog"))
    player.deck = [get_card("Copper") for _ in range(3)]
    gold = get_card("Gold")
    state.gain_card(player, gold)
    assert gold in player.hand  # Sheepdog draws the redirected top card.
    assert any(c.name == "Sleigh" for c in player.discard)
    assert any(c.name == "Sheepdog" for c in player.in_play)


def test_sleigh_does_not_move_gain_after_watchtower():
    strategy = EnhancedStrategy()
    strategy.choose_watchtower_reaction = lambda s, p, c: "topdeck"
    strategy.choose_sleigh_reaction = lambda s, p, c: "hand"
    state, player = setup(strategy, ("Watchtower", "Sleigh"))
    gold = get_card("Gold")
    state.gain_card(player, gold)
    assert gold in player.deck
    assert gold not in player.hand
    assert any(c.name == "Sleigh" for c in player.discard)


@pytest.mark.parametrize("discard", [True, False])
@pytest.mark.parametrize("names", [(), ("Gold",), ("Gold", "Silver", "Copper")])
@pytest.mark.parametrize("curses", [0, 1])
def test_torturer_both_hooks_use_responder_and_honor_choices(discard, names, curses):
    state, attacker = setup(opponents=1)
    target = state.players[1]
    target.hand = [get_card(n) for n in names]
    original = list(target.hand)
    calls = []
    strategy = target.ai.strategy
    strategy.choose_torturer_response = lambda s, p: calls.append(("response", p)) or discard

    def select(s, p, choices, count, *, reason):
        assert s.current_player is attacker
        calls.append((reason, p, count))
        return choices[:count]

    strategy.choose_cards_to_discard = select
    state.supply["Curse"] = curses
    play(state, attacker, get_card("Torturer"))
    assert calls[0] == ("response", target)
    if discard:
        assert calls[1] == ("torturer", target, min(2, len(original)))
        assert len(target.hand) == max(0, len(original) - 2)
        assert state.supply["Curse"] == curses
    else:
        assert len(calls) == 1
        assert len(target.hand) == len(original) + curses
        assert state.supply["Curse"] == 0


@pytest.mark.parametrize("answer", [None, [], [get_card("Gold")], "duplicates", "short"])
def test_torturer_invalid_or_short_discards_are_filled(answer):
    state, attacker = setup(opponents=1)
    target = state.players[1]
    target.hand = [get_card("Estate"), get_card("Estate"), get_card("Gold")]
    original = list(target.hand)
    target.ai.strategy.choose_torturer_response = lambda s, p: True
    target.ai.strategy.choose_cards_to_discard = lambda s, p, c, n, **kw: (
        [c[0], c[0]] if answer == "duplicates" else [c[0]] if answer == "short" else answer)
    play(state, attacker, get_card("Torturer"))
    assert target.hand == [original[-1]]
    assert target.discard == original[:2]
    assert state.supply["Curse"] == 10


@pytest.mark.parametrize("reaction", ["trash", "topdeck", None])
def test_torturer_curse_destination_respects_watchtower(reaction):
    state, attacker = setup(opponents=1)
    target = state.players[1]
    target.hand = [get_card("Watchtower")]
    target.ai.strategy.choose_torturer_response = lambda s, p: False
    target.ai.strategy.choose_watchtower_reaction = lambda s, p, c: reaction
    play(state, attacker, get_card("Torturer"))
    destination = state.trash if reaction == "trash" else target.deck if reaction == "topdeck" else target.hand
    assert sum(c.name == "Curse" for c in destination) == 1
    assert sum(c.name == "Curse" for c in target.all_cards()) == (0 if reaction == "trash" else 1)


def test_torturer_target_order_starts_left_of_attacker():
    state, first = setup(opponents=2)
    state.current_player_index = 1
    attacker = state.current_player
    seen = []
    for player in state.players:
        player.ai.strategy.choose_torturer_response = lambda s, p: seen.append(p) or False
    state.supply["Curse"] = 1
    play(state, attacker, get_card("Torturer"))
    assert seen == [state.players[2], first]
    assert state.players[2].hand[-1].name == "Curse"
    assert first.hand == []


@pytest.mark.parametrize("names,curses,expected", [
    ((), 10, True), (("Estate",), 10, True), (("Gold",), 10, False),
    (("Province", "Duchy", "Gold"), 10, True),
    (("Copper", "Copper", "Copper", "Copper", "Copper"), 10, True),
    (("Gold", "Gold", "Copper", "Copper", "Estate"), 10, True),
    (("Gold", "Gold", "Copper", "Estate", "Province"), 10, True),
    (("Estate", "Estate"), 0, False),
    (("Smithy", "Smithy", "Smithy", "Gold"), 10, True),
])
def test_torturer_default_uses_responding_hand(names, curses, expected):
    state, attacker = setup(opponents=1)
    target = state.players[1]
    target.hand = [get_card(n) for n in names]
    state.supply["Curse"] = curses
    assert target.ai.choose_torturer_attack(state, target) is expected


def test_torturer_discard_reactions_do_not_change_selected_batch():
    state, attacker = setup(opponents=1)
    target = state.players[1]
    target.hand = [get_card("Trail"), get_card("Tunnel"), get_card("Gold")]
    target.deck = [get_card("Copper") for _ in range(3)]
    target.ai.strategy.action_priority = [PriorityRule("Trail")]
    target.ai.strategy.choose_torturer_response = lambda s, p: True
    target.ai.strategy.choose_cards_to_discard = lambda s, p, c, n, **kw: c[:2]
    play(state, attacker, get_card("Torturer"))
    assert any(c.name == "Trail" for c in target.in_play)
    assert any(c.name == "Tunnel" for c in target.discard)
    assert sum(c.name == "Gold" for c in target.all_cards()) == 2
    assert sum(c.name == "Copper" for c in target.hand) == 1


@pytest.mark.parametrize("answers", [(False, False), (False, True), (True, False)])
def test_throne_room_retains_barge_until_all_delayed_payloads_resolve(answers):
    state, player = setup(names=("Barge",))
    decisions = iter(answers)
    player.ai.strategy.should_resolve_barge_now = lambda s, p: next(decisions)
    barge = player.hand[0]
    player.deck = [get_card("Copper") for _ in range(15)]
    throne = get_card("Throne Room")
    play(state, player, throne)
    state.handle_cleanup_phase()
    assert barge in player.in_play
    assert throne in player.in_play
    before = len(player.hand)
    state.do_duration_phase()
    assert len(player.hand) == before + 3 * answers.count(False)
    assert not player.duration
    state.handle_cleanup_phase()
    assert barge not in player.in_play
    assert throne not in player.in_play


@pytest.mark.parametrize("now", [True, False])
def test_barge_chameleon_swaps_only_immediate_draw(now):
    from dominion.ways.chameleon import WayOfTheChameleon

    state, player = setup()
    player.ai.strategy.should_resolve_barge_now = lambda s, p: now
    player.ai.strategy.choose_way = lambda s, p, c, ways: ways[0]
    state.ways = [WayOfTheChameleon()]
    player.deck = [get_card("Copper") for _ in range(10)]
    play(state, player, get_card("Barge"))
    assert player.coins == (3 if now else 0)
    assert player.hand == []
    state.do_duration_phase()
    assert len(player.hand) == (0 if now else 3)
    assert player.coins == (3 if now else 0)


def test_torturer_moat_blocks_both_decision_hooks():
    state, attacker = setup(opponents=1)
    target = state.players[1]
    target.hand = [get_card("Moat")]
    calls = []
    target.ai.strategy.choose_torturer_response = lambda s, p: calls.append(p) or False
    play(state, attacker, get_card("Torturer"))
    assert calls == []
    assert state.supply["Curse"] == 10


def test_sleigh_default_preserves_reaction_after_another_gain_mover():
    state, player = setup(names=("Watchtower", "Sleigh"))
    player.ai.strategy.choose_watchtower_reaction = lambda s, p, c: "topdeck"
    gold = get_card("Gold")
    state.gain_card(player, gold)
    assert gold in player.deck
    assert any(c.name == "Sleigh" for c in player.hand)


def test_sleigh_declining_first_copy_allows_second_copy_to_react():
    state, player = setup(names=("Sleigh", "Sleigh"))
    answers = iter([None, "deck"])
    player.ai.strategy.choose_sleigh_reaction = lambda s, p, c: next(answers)
    first, second = player.hand
    gold = get_card("Gold")
    state.gain_card(player, gold)
    assert first in player.hand
    assert second in player.discard
    assert gold in player.deck



def test_purchase_preserving_torturer_response_remains_an_opt_in_strategy_choice():
    from dominion.ai.tactical_defaults import torturer_should_discard_preserving_buy

    state, attacker = setup(opponents=1)
    target = state.players[1]
    target.hand = [get_card("Copper") for _ in range(5)]
    assert target.ai.choose_torturer_attack(state, target)
    target.ai.strategy.choose_torturer_response = torturer_should_discard_preserving_buy
    assert not target.ai.choose_torturer_attack(state, target)

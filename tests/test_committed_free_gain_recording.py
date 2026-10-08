"""Teacher observations describe committed actions, never speculative pairs."""
from types import SimpleNamespace

import pytest

from dominion.ai.genetic_ai import GeneticAI
from dominion.cards.registry import get_card
from dominion.rl.action_encoder import ActionEncoder
from dominion.rl.general.encoding import CARD_POOL
from dominion.rl.general.train import RecordingTeacher
from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule
from tests.test_shared_card_tactics import make_state


def teacher_state(names=("Village", "Silver", "Curse"), strategy=None):
    strategy = strategy or EnhancedStrategy()
    strategy.free_gain_priority = [PriorityRule("Village")]
    teacher = RecordingTeacher.__new__(RecordingTeacher)
    GeneticAI.__init__(teacher, strategy)
    teacher.examples = []
    # Reaction fixtures extend the test vocabulary, not the training vocabulary.
    teacher.actions = ActionEncoder(list(CARD_POOL) + ["Market Square", "Fortress", "Trader", "Watchtower"])
    teacher.encoder = SimpleNamespace(encode_decision=lambda state, seat, decision: {
        "hand": tuple(c.name for c in state.players[seat].hand),
        "discard": tuple(c.name for c in state.players[seat].discard),
        "trash": tuple(c.name for c in state.trash),
        "supply": state.supply.copy(),
        "stored": tuple(c.name for qm in state.players[seat].duration for c in getattr(qm, "set_aside", [])),
    })
    state, player = make_state(names=names)
    player.ai = teacher
    return state, player, teacher


def labels(teacher):
    return [(decision, teacher.actions.action_to_card(target).name) for _, _, target, decision in teacher.examples]


def test_remodel_market_square_consumes_provisional_gold_and_records_final_fallback():
    state, player, teacher = teacher_state(("Gold", "Smithy", "Village", "Curse"))
    teacher.strategy.free_gain_priority = [PriorityRule("Gold"), PriorityRule("Smithy")]
    teacher.strategy.trash_priority = [PriorityRule("Smithy")]
    player.hand = [get_card("Smithy"), get_card("Market Square")]
    state.supply["Gold"] = 1
    get_card("Remodel").play_effect(state)
    assert labels(teacher) == [("trash", "Smithy"), ("buy", "Smithy")]
    before_trash, _, _, _ = teacher.examples[0]
    before_gain, _, _, _ = teacher.examples[1]
    assert before_trash["hand"] == ("Smithy", "Market Square") and before_trash["trash"] == ()
    assert before_gain["supply"]["Gold"] == 0 and before_gain["supply"]["Smithy"] == 10
    assert before_gain["trash"] == ("Smithy",)
    assert before_gain["discard"] == ("Market Square", "Gold")
    assert state.supply["Smithy"] == 9


def test_remodel_post_trash_empty_menu_records_only_actual_trash():
    state, player, teacher = teacher_state(("Gold", "Province"))
    teacher.strategy.trash_priority = [PriorityRule("Smithy")]
    teacher.strategy.free_gain_priority = [PriorityRule("Gold")]
    player.hand = [get_card("Smithy"), get_card("Market Square")]
    state.supply["Gold"] = 1
    get_card("Remodel").play_effect(state)
    assert labels(teacher) == [("trash", "Smithy")]
    assert state.supply["Gold"] == 0


@pytest.mark.parametrize("source", ["Workshop", "Remodel", "Anvil", "Quartermaster"])
@pytest.mark.parametrize("outcome", ["success", "failed", "trader", "topdeck", "trash", "empty"])
def test_all_effects_commit_only_successful_matching_gains(source, outcome, monkeypatch):
    state, player, teacher = teacher_state(("Province",) if outcome == "empty" else ("Village", "Silver", "Curse"))
    player.hand = [get_card("Copper")]
    if source == "Remodel":
        player.hand = [get_card("Estate")]
    if outcome in {"topdeck", "trash"}:
        player.hand.append(get_card("Watchtower"))
        teacher.strategy.choose_watchtower_reaction = lambda *args: outcome
    if outcome == "trader":
        player.hand.append(get_card("Trader"))
        teacher.should_reveal_trader = lambda *args, **kwargs: True
    if outcome == "failed":
        monkeypatch.setattr(state, "gain_card", lambda *args, **kwargs: None)
    if source == "Quartermaster":
        player.duration = [get_card(source)]
        state._handle_quartermaster_start_of_turn(player)
    else:
        get_card(source).play_effect(state)
    gain_examples = [e for e in teacher.examples if e[3] == "buy"]
    if outcome in {"failed", "trader", "empty"}:
        assert gain_examples == []
        return
    assert len(gain_examples) == 1
    observation, mask, target, _ = gain_examples[0]
    assert target == teacher.actions.card_to_action(get_card("Village")) and mask[target]
    assert observation["supply"]["Village"] == 10 and state.supply["Village"] == 9
    assert observation["stored"] == ()
    destination = player.deck if outcome == "topdeck" else state.trash if outcome == "trash" else player.duration[0].set_aside if source == "Quartermaster" else player.discard
    assert destination[-1].name == "Village"


def test_quartermaster_take_does_not_create_a_gain_example():
    state, player, teacher = teacher_state()
    qm = get_card("Quartermaster")
    qm.set_aside = [get_card("Village"), get_card("Silver")]
    player.duration = [qm]
    teacher.strategy.choose_quartermaster_option = lambda state, player, mat, candidates: ("take", mat[0])
    state._handle_quartermaster_start_of_turn(player)
    assert teacher.examples == []
    assert player.hand[-1].name == "Village" and qm.set_aside[0].name == "Silver"


def test_legacy_remodel_selector_records_trash_once_after_commit():
    legacy = SimpleNamespace(choose_trash=lambda state, player, choices: choices[0],
                             choose_gain=lambda state, player, choices: choices[0])
    state, player, teacher = teacher_state(strategy=legacy)
    player.hand = [get_card("Estate"), get_card("Copper")]
    get_card("Remodel").play_effect(state)
    assert labels(teacher).count(("trash", "Estate")) == 1
    assert not teacher._planning_remodel


def test_failed_remodel_trash_and_selector_exception_do_not_commit(monkeypatch):
    state, player, teacher = teacher_state()
    player.hand = [get_card("Estate"), get_card("Copper")]
    def fail(*args):
        raise RuntimeError("failed operation")
    monkeypatch.setattr(state, "trash_card", fail)
    with pytest.raises(RuntimeError):
        get_card("Remodel").play_effect(state)
    assert teacher.examples == [] and not teacher._planning_remodel
    monkeypatch.setattr(teacher.strategy, "choose_remodel_option", fail)
    with pytest.raises(RuntimeError):
        teacher.choose_remodel_option(state, player, [])
    assert not teacher._planning_remodel


def test_fortress_return_is_still_a_committed_trash():
    state, player, teacher = teacher_state()
    teacher.strategy.trash_priority = [PriorityRule("Fortress")]
    fortress = get_card("Fortress")
    player.hand = [fortress, get_card("Copper")]
    get_card("Remodel").play_effect(state)
    assert labels(teacher) == [("trash", "Fortress"), ("buy", "Village")]
    assert fortress in player.hand and fortress not in state.trash


def test_invalid_joint_remodel_pair_records_only_executed_fallback():
    state, player, teacher = teacher_state()
    teacher.strategy.choose_remodel_option = lambda *args: (get_card("Gold"), get_card("Province"))
    player.hand = [get_card("Estate"), get_card("Copper")]
    get_card("Remodel").play_effect(state)
    assert len([e for e in teacher.examples if e[3] == "trash"]) == 1
    assert labels(teacher)[0][1] == state.trash[0].name
    assert all(name != "Gold" for _, name in labels(teacher))


def test_stale_exposed_gain_never_prepares_or_commits_a_teacher_example():
    from dominion.cards.gain_decisions import gain_selected
    state, player, teacher = teacher_state(("Catapult", "Rocks", "Village"))
    stale = get_card("Catapult")
    state.rotate_supply_pile("Catapult")
    result = gain_selected(state, player, stale, choices=[stale, get_card("Village")], source="Workshop")
    assert result is None and teacher.examples == []
    assert state.top_supply_card("Catapult") == "Rocks"

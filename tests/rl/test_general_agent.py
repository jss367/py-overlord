"""Generalization boundaries, hidden information, and real-game integration."""

from copy import deepcopy

import numpy as np
import pytest
import torch

from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.rl.env import DominionEnv, game_reward
from dominion.rl.general.encoding import CARD_POOL, GeneralEncoder, kingdom_splits, validate_splits
from dominion.rl.general.evaluate import evaluate_policy, play_game, summarize
from dominion.rl.general.opponents import make_opponent
from dominion.rl.general.policy import GeneralAI, GeneralPolicy, load_checkpoint, save_checkpoint
from dominion.rl.general.train import collect_examples, imitate, OpponentLeague
from dominion.rl.ppo import PPOTrainer
from dominion.rl.rl_ai import RLAI


def setup_state():
    board = kingdom_splits()["train"][0]
    state = GameState(players=[], supply={})
    state.log_callback = lambda msg: None
    state.initialize_game([make_opponent("draw_money", board), make_opponent("big_money", board)],
                          [get_card(n) for n in board])
    return state


def test_kingdoms_are_disjoint_reproducible_and_order_independent():
    splits = kingdom_splits()
    validate_splits(splits)
    assert splits == kingdom_splits()
    assert splits != kingdom_splits(seed=12)
    broken = deepcopy(splits)
    broken["test"][0] = list(reversed(splits["train"][0]))
    with pytest.raises(ValueError, match="overlap"):
        validate_splits(broken)


def test_observation_cannot_see_hidden_hands_or_draw_order():
    state = setup_state()
    encoder = GeneralEncoder()
    before = encoder.encode_decision(state, 0, "buy")
    state.players[0].deck.reverse()
    state.players[1].deck.reverse()
    state.players[1].hand = [get_card("Gold") for _ in state.players[1].hand]
    state.players[1].deck = [get_card("Province") for _ in state.players[1].deck]
    np.testing.assert_array_equal(before, encoder.encode_decision(state, 0, "buy"))
    state.players[0].hand.append(get_card("Silver"))
    assert not np.array_equal(before, encoder.encode_decision(state, 0, "buy"))


def test_decision_type_and_supply_presence_are_observable():
    state = setup_state()
    encoder = GeneralEncoder()
    buy = encoder.encode_decision(state, 0, "buy")
    assert buy.shape == (encoder.observation_size,)
    assert not np.array_equal(buy, encoder.encode_decision(state, 0, "trash"))
    state.supply["Chapel"] = 0
    exhausted = encoder.encode_decision(state, 0, "buy")
    del state.supply["Chapel"]
    assert not np.array_equal(exhausted, encoder.encode_decision(state, 0, "buy"))


def test_environment_switches_kingdom_and_seat_with_fixed_shapes():
    boards = kingdom_splits()["train"][:2]
    env = DominionEnv(boards[0], kingdoms=boards, vocabulary=CARD_POOL,
                      state_encoder=GeneralEncoder())
    try:
        for seat, board in enumerate(boards):
            obs, info = env.reset(seed=45, options={"kingdom": board, "seat": seat})
            assert info["kingdom"] == board and info["seat"] == seat
            assert obs.shape == env.observation_space.shape
            assert info["action_mask"].shape == (env.action_space.n,)
            with pytest.raises(ValueError, match="Illegal"):
                env.step(-1)
    finally:
        env.close()


def test_reset_and_close_really_stop_old_game_threads():
    board = kingdom_splits()["train"][0]
    env = DominionEnv(board)
    old_threads = []
    for _ in range(5):
        env.reset(seed=1)
        old_threads.append(env._game_thread)
    env.close()
    assert all(not t.is_alive() for t in old_threads)


def test_game_errors_propagate_instead_of_becoming_training_rewards():
    board = kingdom_splits()["train"][0]
    opponent = make_opponent("big_money", board)

    def fail(*args):
        raise ValueError("injected rules failure")

    opponent.choose_treasure = fail
    env = DominionEnv(board, opponent)
    try:
        with pytest.raises(RuntimeError, match="engine failed"):
            env.reset(seed=1, options={"seat": 1})
    finally:
        env.close()


def test_turn_cap_is_truncation_not_victory():
    board = kingdom_splits()["train"][0]
    env = DominionEnv(board, max_turns=1)
    try:
        _, info = env.reset(seed=1)
        for _ in range(100):
            _, reward, terminated, truncated, info = env.step(int(np.flatnonzero(info["action_mask"])[0]))
            if terminated or truncated:
                break
        assert truncated and not terminated and reward == 0
        env.close()
    finally:
        env.close()


def test_chapel_menu_allows_stopping_without_trashing():
    ai = RLAI()
    gold = get_card("Gold")
    ai.action_queue.put(None)
    assert ai.choose_card_to_trash(None, [gold]) is None
    decision, _, choices = ai.choice_queue.get_nowait()
    assert decision == "trash"
    assert choices == [gold, None]


def test_score_tiebreak_uses_turns_taken():
    state = setup_state()
    state.players[0].turns_taken = 10
    state.players[1].turns_taken = 9
    assert game_reward(state, 0) == -1
    assert game_reward(state, 1) == 1
    state.players[1].turns_taken = 10
    assert game_reward(state, 0) == 0


def test_checkpoint_roundtrip_and_schema_rejection(tmp_path):
    torch.set_num_threads(1)
    policy = GeneralPolicy()
    path = tmp_path / "agent.pt"
    save_checkpoint(path, policy, {"splits": kingdom_splits()})
    loaded, metadata = load_checkpoint(path)
    obs = torch.zeros(1, GeneralEncoder.observation_size)
    torch.testing.assert_close(policy(obs)[0], loaded(obs)[0])
    assert metadata["splits"] == kingdom_splits()
    payload = torch.load(path, weights_only=True)
    payload["vocabulary"].reverse()
    torch.save(payload, path)
    with pytest.raises(ValueError, match="incompatible"):
        load_checkpoint(path)


def test_policy_respects_legal_choices_and_actual_card_instances():
    state = setup_state()
    ai = GeneralAI(GeneralPolicy())
    state.players[0].ai = ai
    assert not state._all_decision_hooks_pure()
    silver = get_card("Silver")
    assert ai.choose_buy(state, [silver]) is silver
    assert ai.choose_action(state, [None]) is None
    state.original_kingdom_pile_names.add("King's Court")
    with pytest.raises(ValueError, match="ten distinct"):
        GeneralAI(GeneralPolicy()).choose_buy(state, [silver])


def test_imitation_and_ppo_update_one_shared_policy():
    torch.set_num_threads(1)
    torch.manual_seed(7)
    boards = kingdom_splits()["train"][:2]
    policy = GeneralPolicy()
    before = deepcopy(policy.state_dict())
    examples = collect_examples(boards, games=3, seed=7)
    losses = imitate(policy, examples, epochs=1, seed=7)
    assert np.isfinite(losses).all()
    assert any(not torch.equal(before[k], v) for k, v in policy.state_dict().items())
    league = OpponentLeague(policy, seed=8)
    frozen = deepcopy(league.peers[0].state_dict())
    env = DominionEnv(boards[0], league, kingdoms=boards, vocabulary=CARD_POOL,
                      state_encoder=GeneralEncoder(), randomize_seats=True)
    try:
        trainer = PPOTrainer(env, policy=policy, seed=7, rollout_steps=32, ppo_epochs=1)
        result = trainer.train_iteration()
        assert np.isfinite(list(result.values())).all()
        for key, value in league.peers[0].state_dict().items():
            torch.testing.assert_close(value, frozen[key])
    finally:
        env.close()


def test_evaluation_pairs_seats_reproduces_results_and_counts_caps():
    torch.set_num_threads(1)
    policy = GeneralPolicy()
    boards = kingdom_splits()["test"][:1]
    a = evaluate_policy(policy, boards, pairs=1, baselines=("big_money",), max_turns=1)
    b = evaluate_policy(policy, boards, pairs=1, baselines=("big_money",), max_turns=1)
    assert a == b
    games = a["kingdom_results"][0]["individual_games"]
    assert [g["seat"] for g in games] == [0, 1]
    assert games[0]["seed"] == games[1]["seed"]
    assert a["totals"]["big_money"]["truncated"] == 2
    assert a["totals"]["big_money"]["score_rate"] == 0
    assert summarize([dict(reward=0, truncated=False, vp=3, opponent_vp=3)])["score_rate"] == .5


def test_complete_baseline_games_are_reproducible_in_both_seats():
    board = kingdom_splits()["validation"][0]
    for seat in (0, 1):
        results = [play_game(board, make_opponent("draw_money", board),
                             make_opponent("big_money", board), 913, seat)
                   for _ in range(2)]
        assert results[0] == results[1]
        assert not results[0]["truncated"]

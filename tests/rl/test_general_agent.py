"""Generalization boundaries, hidden information, and real-game integration."""

from copy import deepcopy

import numpy as np
import pytest
import torch

from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.rl.env import DominionEnv, episode_status, game_reward
from dominion.rl.general.encoding import CARD_POOL, GeneralEncoder, kingdom_splits, validate_splits
from dominion.rl.general.evaluate import evaluate_policy, play_game, summarize
from dominion.rl.general.opponents import make_opponent
from dominion.rl.general.policy import GeneralAI, GeneralPolicy, load_checkpoint, save_checkpoint
from dominion.rl.general.train import collect_examples, imitate, OpponentLeague
from dominion.rl.ppo import PPOTrainer
from dominion.rl.rl_ai import RLAI
from dominion.rl.random_ai import RandomAI


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


class PassingAI(RandomAI):
    """Leave every pile untouched so only the safety cap ends the game."""

    def choose_action(self, state, choices):
        return None

    def choose_treasure(self, state, choices):
        return None

    def choose_buy(self, state, choices):
        return None


@pytest.mark.parametrize("max_turns", [100, 150])
def test_engine_turn_cap_truncates_training_without_a_winning_reward(max_turns):
    board = kingdom_splits()["train"][0]
    env = DominionEnv(board, PassingAI(), max_turns=max_turns)
    try:
        env.reset(seed=1)
        env.game_state.turn_number = 100
        env.game_state.players[0].vp_tokens = 10
        for _ in range(30):
            _, reward, terminated, truncated, _ = env.step(env.action_encoder.pass_action_index)
            if terminated or truncated:
                break
        assert truncated and not terminated and reward == 0
        assert env.game_state.turn_number == 101
    finally:
        env.close()


@pytest.mark.parametrize("seat", [0, 1])
@pytest.mark.parametrize("max_turns", [1, 100, 150])
def test_truncation_returns_next_real_decision_after_opponent_turn(seat, max_turns):
    board = kingdom_splits()["train"][0]
    encoder = GeneralEncoder()
    env = DominionEnv(board, PassingAI(), max_turns=max_turns, state_encoder=encoder)
    try:
        env.reset(seed=1, options={"seat": seat})
        env.game_state.turn_number = min(max_turns, 100)
        opponent = env.game_state.players[1 - seat]
        previous_opponent_turns = opponent.turns_taken
        for _ in range(30):
            obs, reward, terminated, truncated, info = env.step(env.action_encoder.pass_action_index)
            if terminated or truncated:
                break
        assert truncated and not terminated and reward == 0
        assert env.game_state.current_player_index == seat
        assert env.game_state.phase != "start"
        assert opponent.turns_taken == previous_opponent_turns + 1
        assert info["decision_type"] in ("action", "treasure", "buy", "trash")
        assert obs[-4:].sum() == 1
        np.testing.assert_array_equal(
            obs, encoder.encode_decision(env.game_state, seat, info["decision_type"]))
        # Truncation leaves the engine suspended at this exact decision;
        # close must cancel it without executing an unrecorded agent action.
        thread = env._game_thread
        assert thread.is_alive()
        env.close()
        assert not thread.is_alive()
    finally:
        env.close()


@pytest.mark.parametrize("max_turns", [1, 100, 150])
def test_natural_end_before_post_cap_decision_is_terminal(max_turns):
    cap = min(max_turns, 100)

    class EndingOpponent(PassingAI):
        def choose_buy(self, state, choices):
            if state.turn_number > cap:
                state.supply["Province"] = 0
            return None

    board = kingdom_splits()["train"][0]
    env = DominionEnv(board, EndingOpponent(), max_turns=max_turns)
    try:
        env.reset(seed=1, options={"seat": 1})
        env.game_state.turn_number = cap
        env.game_state.players[1].vp_tokens = 10
        for _ in range(30):
            _, reward, terminated, truncated, info = env.step(env.action_encoder.pass_action_index)
            if terminated or truncated:
                break
        assert terminated and not truncated and reward == 1
        assert not info["decision_type"]
    finally:
        env.close()


@pytest.mark.parametrize("max_turns", [100, 150])
def test_engine_turn_cap_receives_no_evaluation_credit(monkeypatch, max_turns):
    original = GameState.initialize_game

    def start_near_cap(state, *args, **kwargs):
        original(state, *args, **kwargs)
        state.turn_number = 100
        state.players[0].vp_tokens = 10

    monkeypatch.setattr(GameState, "initialize_game", start_near_cap)
    board = kingdom_splits()["test"][0]
    game = play_game(board, PassingAI(), PassingAI(), 1, 0, max_turns)
    assert game["turns"] == 101
    assert game["truncated"] and game["reward"] is None
    assert summarize([game])["score_rate"] == 0


@pytest.mark.parametrize("max_turns", [1, 100, 150])
def test_natural_ending_wins_over_cap_on_the_same_boundary(max_turns):
    state = setup_state()
    state.turn_number = min(max_turns, 100) + 1
    state.supply["Province"] = 0
    assert episode_status(state, max_turns) == (True, False)


@pytest.mark.parametrize("max_turns", [1, 100, 150])
def test_fleet_round_finishes_after_crossing_turn_cap(max_turns):
    from dominion.projects.fleet import Fleet

    state = setup_state()
    state.turn_number = min(max_turns, 100) + 1
    state.supply["Province"] = 0
    for player in state.players:
        player.ai = PassingAI()
        player.projects.append(Fleet())
    before = [p.turns_taken for p in state.players]
    assert episode_status(state, max_turns) == (False, False)
    assert state.fleet_extra_round_active
    for _ in range(30):
        terminated, truncated = episode_status(state, max_turns)
        assert not truncated
        if terminated:
            break
        state.play_turn()
    assert terminated
    assert [p.turns_taken for p in state.players] == [n + 1 for n in before]
    assert not state.fleet_extra_players


@pytest.mark.parametrize("max_turns", [1, 100, 150])
@pytest.mark.parametrize("end_after_cap", [False, True])
def test_training_finishes_fleet_even_when_truncation_was_pending(max_turns, end_after_cap):
    from dominion.projects.fleet import Fleet

    cap = min(max_turns, 100)

    class EndingOpponent(PassingAI):
        def choose_buy(self, state, choices):
            if state.turn_number > cap:
                state.supply["Province"] = 0
            return None

    board = kingdom_splits()["train"][0]
    env = DominionEnv(board, EndingOpponent(), max_turns=max_turns)
    try:
        env.reset(seed=1, options={"seat": 1})
        state = env.game_state
        state.turn_number = cap
        if not end_after_cap:
            state.supply["Province"] = 0
        for player in state.players:
            player.projects.append(Fleet())
        before = [p.turns_taken for p in state.players]
        for _ in range(60):
            _, _, terminated, truncated, _ = env.step(env.action_encoder.pass_action_index)
            assert not truncated
            if terminated:
                break
        assert terminated and state.fleet_extra_round_active
        assert not state.fleet_extra_players
        assert state.players[1].turns_taken == before[1] + 1
        assert state.players[0].turns_taken == before[0] + 1 + end_after_cap
    finally:
        env.close()


def test_chapel_menu_allows_stopping_without_trashing():
    state = setup_state()
    ai = RLAI()
    gold = get_card("Gold")
    state.players[0].ai = ai
    state.players[0].hand = [gold]
    ai.action_queue.put(None)
    get_card("Chapel").play_effect(state)
    decision, _, choices = ai.choice_queue.get_nowait()
    assert decision == "trash"
    assert choices == [gold, None]
    assert state.players[0].hand == [gold]
    assert not state.trash


@pytest.mark.parametrize("card_name", ["Rats", "Temple"])
def test_mandatory_trash_effects_do_not_offer_pass(card_name):
    state = setup_state()
    ai = RLAI()
    estate = get_card("Estate")
    state.players[0].ai = ai
    state.players[0].hand = [estate]
    ai.action_queue.put(estate)
    get_card(card_name).play_effect(state)
    decision, _, choices = ai.choice_queue.get_nowait()
    assert decision == "trash" and choices == [estate]
    assert estate in state.trash
    from dominion.rl.action_encoder import ActionEncoder
    encoder = ActionEncoder([card_name])
    assert not encoder.get_action_mask(choices)[encoder.pass_action_index]


@pytest.mark.parametrize("card_name", ["Goat", "Masquerade"])
def test_legacy_random_opponent_can_decline_optional_trash(monkeypatch, card_name):
    """Keep legacy optional effects working without changing the shared sampler."""
    import random

    state = setup_state()
    state.players[0].ai = RandomAI()
    for player in state.players:
        player.hand = [get_card("Gold")]
    monkeypatch.setattr(random, "choice", lambda choices: choices[-1])
    get_card(card_name).play_effect(state)
    assert not state.trash
    assert [c.name for c in state.players[0].hand] == ["Gold"]


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
    assert ai.choose_card_to_trash(state, [silver]) is silver
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

"""Printed-rule regressions for the Recruiter / Kitsune board."""

from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState
from dominion.prophecies.registry import get_prophecy
from tests.utils import DummyAI


class ChoicesAI(DummyAI):
    def choose_action(self, state, choices):
        return next((c for c in choices if c and c.name == "Villa"), None)

    def choose_buy(self, state, choices):
        return next((c for c in choices if c and c.name == "Villa"), None)

    def choose_kitsune_options(self, state, player, options):
        return ["action", "coins"]

    def choose_card_to_trash(self, state, choices):
        return choices[0] if choices else None

    def choose_treasure(self, state, choices):
        return next((c for c in choices if c and c.name == "Anvil"), None)

    def choose_anvil_gain(self, state, player, choices):
        return next(c for c in choices if c.name == "Villa")

    def choose_anvil_treasure_to_discard(self, state, player, choices):
        return choices[0]


def state_and_player():
    player = PlayerState(ChoicesAI())
    other = PlayerState(DummyAI())
    state = GameState([player, other])
    state.log_callback = lambda *_: None
    state.supply = {"Villa": 10, "Engineer": 10, "Province": 8}
    return state, player


def test_kitsune_actions_and_prophecy_activation():
    state, player = state_and_player()
    state.prophecy = get_prophecy("Great Leader")
    state.sun_tokens = 1
    player.actions = 0
    get_card("Kitsune").on_play(state)
    assert state.sun_tokens == 0
    assert state.prophecy.is_active
    assert player.actions == 2
    assert player.coins == 2


def test_inventor_is_terminal_and_cannot_gain_engineer():
    state, player = state_and_player()
    state.supply = {"Engineer": 10}
    player.actions = 0
    get_card("Inventor").on_play(state)
    assert player.actions == 0
    assert player.cost_reduction == 1
    assert not player.discard
    assert state.supply["Engineer"] == 10


def test_engineer_cost_and_gain_menu_use_all_cost_components():
    state, player = state_and_player()
    engineer = get_card("Engineer")
    assert (engineer.cost.coins, engineer.cost.debt) == (0, 4)
    state.supply = {"Engineer": 10, "Alchemist": 10, "Kitsune": 10}
    player.cost_reduction = 1
    engineer.play_effect(state)
    assert [c.name for c in player.discard] == ["Kitsune"]


def test_recruiter_villagers_use_reduced_cost():
    state, player = state_and_player()
    player.cost_reduction = 2
    player.hand = [get_card("Silver")]
    get_card("Recruiter").play_effect(state)
    assert player.villagers == 1
    assert [c.name for c in state.trash] == ["Silver"]


def test_villa_gained_to_deck_moves_to_hand_and_adds_one_action():
    state, player = state_and_player()
    state.phase = "buy"
    player.actions = 0
    villa = get_card("Villa")
    state.gain_card(player, villa, to_deck=True)
    assert villa in player.hand
    assert villa not in player.deck
    assert player.actions == 1
    assert state.phase == "action"


def test_off_turn_villa_does_not_change_active_players_phase():
    state, player = state_and_player()
    state.phase = "buy"
    state.gain_card(state.players[1], get_card("Villa"))
    assert state.phase == "buy"
    assert state.current_player is player


def test_anvil_villa_returns_from_treasures_to_actions():
    state, player = state_and_player()
    state.phase = "treasure"
    player.actions = 0
    player.hand = [get_card("Anvil"), get_card("Copper"), get_card("Gold")]
    state.handle_treasure_phase()
    assert state.phase == "action"
    assert player.actions == 1
    assert any(c.name == "Villa" for c in player.hand)
    assert any(c.name == "Gold" for c in player.hand)
    assert player.coins == 1


def test_buy_villa_then_anvil_villa_resolves_both_action_returns():
    state, player = state_and_player()
    state.phase = "buy"
    player.actions = 0
    player.coins = 4
    player.buys = 1
    player.hand = [get_card("Anvil"), get_card("Copper")]
    state.handle_buy_phase()
    assert [c.name for c in player.in_play] == ["Villa", "Anvil", "Villa"]
    assert player.coins == 3
    assert state.supply["Villa"] == 8
    assert state.phase == "night"


def test_courtyard_policy_keeps_playable_draw_and_topdecks_junk():
    from dominion.ai.genetic_ai import GeneticAI
    from dominion.strategy.strategies.recruiter_kitsune import RecruiterKitsune

    state, player = state_and_player()
    player.ai = GeneticAI(RecruiterKitsune())
    state.prophecy = get_prophecy("Great Leader")
    state.prophecy.is_active = True
    choices = [get_card("Courtyard"), get_card("Gold"), get_card("Estate")]
    assert player.ai.choose_card_to_topdeck_for_courtyard(state, player, choices).name == "Estate"


def test_engineer_and_counterfeit_strategy_hooks_are_used():
    from dominion.ai.genetic_ai import GeneticAI
    from dominion.strategy.strategies.recruiter_kitsune import RecruiterKitsune

    state, player = state_and_player()
    player.ai = GeneticAI(RecruiterKitsune(engineer_trash=True))
    assert player.ai.should_trash_engineer_for_extra_gains(state, player, get_card("Engineer"))
    player.hand = [get_card("Gold")]
    assert player.ai.should_replay_treasure_with_counterfeit(state, player, player.hand) is None


def test_published_strategy_matches_frozen_tournament_winner():
    import json
    from pathlib import Path

    from dominion.strategy.strategy_loader import StrategyLoader

    result = json.loads(Path("scripts/data/recruiter_kitsune_tournament.json").read_text())
    strategy = StrategyLoader().get_strategy("Recruiter Kitsune Courtyard Engine")
    assert strategy.params == result["ranking"][0]["spec"]


def test_board_has_requested_cards_and_fixed_prophecy():
    from dominion.boards.loader import load_board

    board = load_board("boards/recruiter_kitsune.txt")
    assert board.kingdom_cards == [
        "Recruiter", "Kitsune", "Inventor", "Treasurer", "Villa", "Village",
        "Courtyard", "Counterfeit", "Anvil", "Engineer",
    ]
    assert board.prophecy == "Great Leader"

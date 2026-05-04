"""Tests for Renaissance Artifacts."""

from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState
from tests.utils import DummyAI


def make_game(kingdom_names: list[str], num_players: int = 2):
    ais = [DummyAI() for _ in range(num_players)]
    state = GameState(players=[])
    state.initialize_game(ais, [get_card(n) for n in kingdom_names])
    return state


def test_artifacts_initialized_when_anchor_in_kingdom():
    state = make_game(["Flag Bearer", "Border Guard", "Treasurer", "Swashbuckler"])
    assert "Flag" in state.artifacts
    assert "Horn" in state.artifacts
    assert "Lantern" in state.artifacts
    assert "Key" in state.artifacts
    assert "Treasure Chest" in state.artifacts


def test_artifacts_not_initialized_without_anchor():
    state = make_game(["Village"])
    assert state.artifacts == {}


def test_take_artifact_transfers_holder():
    state = make_game(["Flag Bearer"])
    p1, p2 = state.players
    state.take_artifact(p1, "Flag")
    assert state.artifacts["Flag"].holder is p1
    state.take_artifact(p2, "Flag")
    assert state.artifacts["Flag"].holder is p2


def test_flag_grants_extra_card_at_holder_turn_start():
    state = make_game(["Flag Bearer"])
    p1, _ = state.players
    state.take_artifact(p1, "Flag")
    state.current_player_index = 0
    p1.deck = [get_card("Copper"), get_card("Silver")]
    p1.hand = []
    state.phase = "start"
    state.handle_start_phase()
    assert len(p1.hand) == 1


def test_key_grants_coin_at_holder_turn_start():
    state = make_game(["Treasurer"])
    p1, _ = state.players
    state.take_artifact(p1, "Key")
    state.current_player_index = 0
    p1.deck = [get_card("Copper")]
    p1.hand = []
    state.phase = "start"
    coins_before = p1.coins
    state.handle_start_phase()
    assert p1.coins == coins_before + 1


def test_treasure_chest_gains_gold_at_buy_phase_start():
    state = make_game(["Swashbuckler"])
    p1, _ = state.players
    state.take_artifact(p1, "Treasure Chest")
    state.current_player_index = 0
    state.phase = "treasure"
    p1.hand = []
    gold_before = state.supply["Gold"]
    state.handle_treasure_phase()
    assert state.supply["Gold"] == gold_before - 1
    assert any(c.name == "Gold" for c in p1.discard)


def test_horn_topdecks_border_guard_in_cleanup():
    state = make_game(["Border Guard"])
    p1 = state.players[0]
    state.take_artifact(p1, "Horn")
    state.current_player_index = 0

    # Stack the deck so Border Guard reveals two non-actions to avoid the
    # artifact-take side effect from triggering on this play.
    bg = get_card("Border Guard")
    p1.in_play.append(bg)
    p1.deck = [get_card("Copper"), get_card("Estate")]
    bg.on_play(state)

    # Border Guard should be flagged for Horn topdeck.
    assert bg.horn_topdeck_pending is True

    # Run cleanup; Border Guard should land on top of deck instead of discard.
    p1.hand = []
    state.phase = "cleanup"
    state.handle_cleanup_phase()
    assert bg in p1.deck or bg in (p1.hand)
    assert bg not in p1.discard


def test_lantern_makes_border_guard_reveal_three():
    state = make_game(["Border Guard"])
    p1 = state.players[0]
    state.take_artifact(p1, "Lantern")
    state.current_player_index = 0

    bg = get_card("Border Guard")
    p1.in_play.append(bg)
    # Three actions on top: should keep one and discard two.
    p1.deck = [
        get_card("Village"),
        get_card("Village"),
        get_card("Village"),
    ]
    deck_before = len(p1.deck)
    bg.on_play(state)
    # 3 cards revealed: 1 kept, 2 discarded.
    assert len(p1.discard) == 2
    assert deck_before - len(p1.deck) == 3

"""Sewers: the extra trash must not re-trigger Sewers ("other than with this")."""

from dominion.ai.genetic_ai import GeneticAI
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState
from dominion.landmarks.registry import get_landmark
from dominion.projects.registry import get_project
from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


def _player_with_sewers(hand):
    strategy = EnhancedStrategy()
    strategy.trash_priority = [PriorityRule("Estate"), PriorityRule("Copper")]
    player = PlayerState(ai=GeneticAI(strategy))
    player.hand = [get_card(n) for n in hand]
    player.projects = [get_project("Sewers")]
    return player


def test_sewers_trashes_exactly_one_extra_card_per_trash():
    player = _player_with_sewers(["Estate", "Estate", "Copper", "Gold"])
    state = GameState(players=[player], supply={"Gold": 30})
    trashed = player.hand.pop(0)

    state.trash_card(player, trashed)

    assert [c.name for c in state.trash] == ["Estate", "Estate"]
    assert sorted(c.name for c in player.hand) == ["Copper", "Gold"]


def test_sewers_extra_trash_still_triggers_other_trash_effects():
    player = _player_with_sewers(["Estate", "Copper", "Gold"])
    state = GameState(players=[player], supply={"Gold": 30})
    state.landmarks = [get_landmark("Tomb")]
    trashed = player.hand.pop(1)

    state.trash_card(player, trashed)

    assert [c.name for c in state.trash] == ["Copper", "Estate"]
    assert player.vp_tokens == 2


def test_sewers_declines_when_no_priority_card_is_in_hand():
    player = _player_with_sewers(["Gold", "Silver"])
    state = GameState(players=[player], supply={"Gold": 30})
    trashed = get_card("Estate")

    state.trash_card(player, trashed)

    assert [c.name for c in state.trash] == ["Estate"]
    assert len(player.hand) == 2

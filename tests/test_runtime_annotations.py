"""Runtime inspection must work when annotation types are not imported."""

import inspect

import pytest

from dominion.ai.genetic_ai import GeneticAI
from dominion.analysis.calibration import evolve_and_evaluate
from dominion.artifacts.base_artifact import Artifact
from dominion.artifacts.flag import Flag
from dominion.artifacts.horn import Horn
from dominion.artifacts.key import Key
from dominion.artifacts.treasure_chest import TreasureChest
from dominion.boons import the_earths_gift
from dominion.game.player_state import PlayerState
from dominion.hexes import resolve_hex


@pytest.mark.parametrize(
    "target",
    [
        PlayerState,
        GeneticAI.choose_action,
        evolve_and_evaluate,
        the_earths_gift,
        resolve_hex,
        Artifact.on_take,
        Flag.on_holder_turn_start,
        Horn.on_holder_play_border_guard,
        Key.on_holder_turn_start,
        TreasureChest.on_holder_buy_phase_start,
    ],
    ids=lambda target: target.__qualname__,
)
def test_runtime_inspection_with_type_checking_imports(target):
    assert inspect.signature(target).parameters
    assert target.__annotations__

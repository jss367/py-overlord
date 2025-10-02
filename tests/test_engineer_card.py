from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState

from tests.utils import DummyAI


class EngineerTestAI(DummyAI):
    """Test double that scripts Engineer gain choices."""

    def __init__(self, gain_queue: list[str], *, trash_engineer: bool):
        super().__init__()
        self._gain_queue = list(gain_queue)
        self._trash_engineer = trash_engineer

    def choose_buy(self, state: GameState, choices):
        while self._gain_queue:
            target = self._gain_queue.pop(0)
            for card in choices:
                if card and card.name == target:
                    return card
        return choices[0] if choices else None

    def should_trash_engineer_for_extra_gains(self, state, player, engineer):
        return self._trash_engineer


class NullChoiceAI(DummyAI):
    """AI stub that never makes an explicit gain choice."""

    def choose_buy(self, state: GameState, choices):
        return None


def _make_state(ai: DummyAI) -> tuple[GameState, PlayerState]:
    player = PlayerState(ai)
    state = GameState(players=[player])
    state.log_callback = lambda msg: None
    state.supply = {}
    return state, player


def test_engineer_gains_selected_card_without_trashing():
    ai = EngineerTestAI(["Silver"], trash_engineer=False)
    state, player = _make_state(ai)

    state.supply.update({"Silver": 5, "Estate": 8})

    engineer = get_card("Engineer")
    player.in_play = [engineer]

    engineer.play_effect(state)

    assert [card.name for card in player.discard] == ["Silver"]
    assert state.supply["Silver"] == 4
    assert engineer in player.in_play
    assert engineer not in state.trash


def test_engineer_can_trash_for_two_additional_gains():
    ai = EngineerTestAI(["Silver", "Village", "Workshop"], trash_engineer=True)
    state, player = _make_state(ai)

    state.supply.update({"Silver": 5, "Village": 5, "Workshop": 5})

    engineer = get_card("Engineer")
    player.in_play = [engineer]

    engineer.play_effect(state)

    assert [card.name for card in player.discard] == ["Silver", "Village", "Workshop"]
    assert state.supply["Silver"] == 4
    assert state.supply["Village"] == 4
    assert state.supply["Workshop"] == 4
    assert engineer not in player.in_play
    assert state.trash and state.trash[-1] is engineer


def test_engineer_defaults_to_best_available_gain_when_ai_abstains():
    ai = NullChoiceAI()
    state, player = _make_state(ai)

    state.supply.update({"Silver": 5, "Estate": 8, "Copper": 46})

    engineer = get_card("Engineer")
    player.in_play = [engineer]

    engineer.play_effect(state)

    assert [card.name for card in player.discard] == ["Silver"]
    assert state.supply["Silver"] == 4

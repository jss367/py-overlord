"""Policy tests for the Bilbao Shaman / Feodum Silver mill seeds."""

from dominion.ai.genetic_ai import GeneticAI
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.strategy.strategies.bilbao_seeds import BilbaoShamanFeodumMill
from dominion.strategy.strategy_loader import StrategyLoader
from tests.utils import DummyAI

BILBAO = [
    "Fool's Gold",
    "Grotto",
    "Shaman",
    "Anvil",
    "Hermit",
    "Sheepdog",
    "Feodum",
    "Wandering Minstrel",
    "Wheelwright",
    "Raider",
]


def _game(strategy):
    state = GameState(players=[])
    state.log_callback = lambda *_: None
    state.initialize_game([GeneticAI(strategy), DummyAI()], [get_card(n) for n in BILBAO])
    for p in state.players:
        p.hand, p.deck, p.discard, p.in_play, p.duration = [], [], [], [], []
        p.actions, p.buys, p.coins = 1, 1, 0
    state.current_player_index = 0
    return state


def _play(state, card_name):
    card = get_card(card_name)
    state.current_player.in_play.append(card)
    card.on_play(state)
    return card


def test_loader_registers_both_mill_configurations():
    loader = StrategyLoader()
    assert loader.get_strategy("Bilbao Shaman Feodum Mill") is not None
    assert loader.get_strategy("Bilbao Shaman Feodum Mill Hybrid") is not None


def test_shaman_trashes_feodum_for_three_silvers_when_mill_is_active():
    state = _game(BilbaoShamanFeodumMill())
    p0 = state.players[0]
    feodum, copper = get_card("Feodum"), get_card("Copper")
    p0.hand = [feodum, copper]
    _play(state, "Shaman")
    assert feodum in state.trash
    assert p0.hand == [copper]
    assert sum(1 for c in p0.discard if c.name == "Silver") == 3


def test_shaman_keeps_feodum_once_the_pile_is_down_to_the_stop_level():
    state = _game(BilbaoShamanFeodumMill(trash_stop_pile=3))
    p0 = state.players[0]
    feodum = get_card("Feodum")
    p0.hand = [feodum]
    state.supply["Feodum"] = 3
    _play(state, "Shaman")
    assert feodum in p0.hand
    assert not state.trash


def test_pair_mode_declines_a_lone_feodum_and_accepts_when_hermit_can_follow():
    state = _game(BilbaoShamanFeodumMill(trash_mode="pair"))
    p0 = state.players[0]
    feodum = get_card("Feodum")
    p0.hand = [feodum, get_card("Copper")]
    _play(state, "Shaman")
    assert feodum in p0.hand, "a single trashed Feodum would just be a gift"

    second = get_card("Feodum")
    p0.hand = [feodum, get_card("Hermit")]
    p0.discard = [second]
    _play(state, "Shaman")
    assert feodum in state.trash, "Hermit in hand can trash the Feodum in discard"

    # Hermit then finds a Feodum already in the trash and trashes the second.
    p0.hand = [get_card("Hermit")]
    p0.hand.pop()
    _play(state, "Hermit")
    assert second in state.trash
    assert sum(1 for c in p0.discard if c.name == "Silver") == 7  # 3 + 3 + Hermit's gain


def test_pair_mode_declines_when_the_first_trash_would_end_the_mill():
    """The first trash gains three Silvers; the promised second trasher would
    then find the mill inactive and leave the opponent a lone Feodum."""
    state = _game(BilbaoShamanFeodumMill(trash_mode="pair"))
    p0 = state.players[0]
    feodum, second = get_card("Feodum"), get_card("Feodum")
    p0.hand = [feodum, second, get_card("Shaman")]
    state.supply["Silver"] = 5
    _play(state, "Shaman")
    assert feodum in p0.hand and second in p0.hand
    assert not state.trash

    state.supply["Silver"] = 10
    _play(state, "Shaman")
    assert feodum in state.trash
    assert second in p0.hand


def test_hermit_gains_shamans_up_to_target_then_silver():
    state = _game(BilbaoShamanFeodumMill(shamans=1))
    p0 = state.players[0]
    _play(state, "Hermit")
    assert [c.name for c in p0.discard] == ["Shaman"]
    p0.discard = []
    p0.deck = [get_card("Shaman")]
    _play(state, "Hermit")
    assert [c.name for c in p0.discard] == ["Silver"]


def test_start_of_turn_gain_takes_a_feodum_back_first():
    state = _game(BilbaoShamanFeodumMill())
    p0 = state.players[0]
    feodum, gold = get_card("Feodum"), get_card("Gold")
    state.trash = [gold, feodum]
    state._handle_shaman_start_of_turn(p0)
    assert feodum in p0.discard
    assert gold in state.trash


def test_hermit_in_play_buys_a_copper_rather_than_becoming_a_madman():
    mill = BilbaoShamanFeodumMill()
    state = _game(mill)
    p0 = state.players[0]
    p0.in_play = [get_card("Hermit")]
    p0.coins = 1
    state.phase = "buy"
    choices = [get_card("Copper"), get_card("Curse"), None]
    pick = mill.choose_gain(state, p0, choices)
    assert pick is not None and pick.name == "Copper"

    lazy = BilbaoShamanFeodumMill(avoid_madman=False)
    assert lazy.choose_gain(state, p0, choices) is None


def test_fodder_feodum_honours_the_feodum_pile_stop():
    mill = BilbaoShamanFeodumMill(trash_stop_pile=3)
    state = _game(mill)
    p0 = state.players[0]
    p0.deck = [get_card("Shaman")]
    p0.coins = 4
    state.phase = "buy"
    choices = [get_card("Feodum"), get_card("Silver"), None]

    state.supply["Feodum"] = 3
    pick = mill.choose_gain(state, p0, choices)
    assert pick is not None and pick.name == "Silver"

    state.supply["Feodum"] = 4
    pick = mill.choose_gain(state, p0, choices)
    assert pick is not None and pick.name == "Feodum"

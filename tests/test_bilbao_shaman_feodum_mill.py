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


def _game(strategy, opponents=1):
    state = GameState(players=[])
    state.log_callback = lambda *_: None
    ais = [GeneticAI(strategy)] + [DummyAI() for _ in range(opponents)]
    state.initialize_game(ais, [get_card(n) for n in BILBAO])
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


def test_pair_mode_accepts_a_pile_of_exactly_six_silvers():
    """Six Silvers minus the first trash's three still leaves the mill active."""
    mill = BilbaoShamanFeodumMill(trash_mode="pair")
    state = _game(mill)
    p0 = state.players[0]
    first, second = get_card("Feodum"), get_card("Feodum")
    p0.hand = [first, second, get_card("Shaman")]
    state.supply["Silver"] = 6
    _play(state, "Shaman")
    assert first in state.trash
    assert second in p0.hand


def test_pair_mode_honours_the_feodum_keep_threshold():
    """With two Feodums and one to keep, the promised second trash would be
    refused at the keep threshold, so the first must not happen either."""
    state = _game(BilbaoShamanFeodumMill(trash_mode="pair", trash_keep_feodums=1))
    p0 = state.players[0]
    feodum, second = get_card("Feodum"), get_card("Feodum")
    p0.hand = [feodum, second, get_card("Shaman")]
    state.supply["Silver"] = 10
    _play(state, "Shaman")
    assert feodum in p0.hand and second in p0.hand
    assert not state.trash

    state = _game(BilbaoShamanFeodumMill(trash_mode="pair", trash_keep_feodums=0))
    p0 = state.players[0]
    feodum, second = get_card("Feodum"), get_card("Feodum")
    p0.hand = [feodum, second, get_card("Shaman")]
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

    # At the stop level, and one above it (the purchase itself would drop
    # the pile to the stop and strand the Feodum), buy Silver instead.
    for pile in (3, 4):
        state.supply["Feodum"] = pile
        pick = mill.choose_gain(state, p0, choices)
        assert pick is not None and pick.name == "Silver", pile

    state.supply["Feodum"] = 5
    pick = mill.choose_gain(state, p0, choices)
    assert pick is not None and pick.name == "Feodum"


def test_fodder_feodum_is_not_bought_on_the_last_trash_turn():
    mill = BilbaoShamanFeodumMill(trash_turn_max=10)
    state = _game(mill)
    p0 = state.players[0]
    p0.deck = [get_card("Shaman")]
    p0.coins = 4
    state.phase = "buy"
    choices = [get_card("Feodum"), get_card("Silver"), None]

    state.turn_number = 10
    pick = mill.choose_gain(state, p0, choices)
    assert pick is not None and pick.name == "Silver"

    state.turn_number = 9
    pick = mill.choose_gain(state, p0, choices)
    assert pick is not None and pick.name == "Feodum"


def test_pair_mode_never_trashes_outside_two_player_games():
    mill = BilbaoShamanFeodumMill(trash_mode="pair")
    state = _game(mill, opponents=2)
    p0 = state.players[0]
    first, second = get_card("Feodum"), get_card("Feodum")
    p0.hand = [first, second, get_card("Shaman")]
    state.supply["Silver"] = 10
    _play(state, "Shaman")
    assert first in p0.hand and second in p0.hand
    assert not state.trash
    # Even a Feodum already in the trash is no guarantee with two opponents.
    state.trash = [get_card("Feodum")]
    _play(state, "Shaman")
    assert first in p0.hand and second in p0.hand


def test_anvil_feodum_gain_honours_the_fodder_headroom():
    mill = BilbaoShamanFeodumMill(anvil_gain="feodum", anvils=3, trash_stop_pile=3)
    state = _game(mill)
    p0 = state.players[0]
    p0.deck = [get_card("Shaman")]
    p0.hand = [get_card("Copper"), get_card("Copper")]
    choices = [get_card("Feodum"), get_card("Silver")]

    state.supply["Feodum"] = 4  # one above the stop: the gain would strand it
    pick = mill.choose_anvil_gain(state, p0, choices)
    assert pick is None or pick.name != "Feodum"

    state.supply["Feodum"] = 5
    pick = mill.choose_anvil_gain(state, p0, choices)
    assert pick is not None and pick.name == "Feodum"


def test_silver_cap_leaves_room_for_the_three_silvers_a_trash_gains():
    mill = BilbaoShamanFeodumMill(trash_silver_cap=12)
    state = _game(mill)
    p0 = state.players[0]
    feodum = get_card("Feodum")
    p0.hand = [feodum]
    p0.deck = [get_card("Silver") for _ in range(10)]
    _play(state, "Shaman")
    assert feodum in p0.hand, "10 + 3 would exceed a cap of 12"

    p0.deck = [get_card("Silver") for _ in range(9)]
    _play(state, "Shaman")
    assert feodum in state.trash
    assert sum(1 for c in p0.all_cards() if c.name == "Silver") == 12


def test_hermit_trash_reserves_room_for_its_own_silver_under_the_cap():
    # shamans=0 so Hermit's own gain is a Silver rather than a Shaman.
    mill = BilbaoShamanFeodumMill(trash_silver_cap=12, shamans=0)
    state = _game(mill)
    p0 = state.players[0]
    feodum = get_card("Feodum")
    p0.discard = [feodum]
    p0.deck = [get_card("Silver") for _ in range(9)]
    _play(state, "Hermit")
    assert feodum in p0.discard, "9 + 3 + Hermit's own Silver would exceed 12"

    p0.discard = [feodum]
    p0.deck = [get_card("Silver") for _ in range(8)]
    _play(state, "Hermit")
    assert feodum in state.trash
    assert sum(1 for c in p0.all_cards() if c.name == "Silver") == 12


def test_pair_mode_counts_the_hermit_follow_up_silver_under_the_cap():
    mill = BilbaoShamanFeodumMill(trash_mode="pair", trash_silver_cap=12)
    state = _game(mill)
    p0 = state.players[0]
    first, second = get_card("Feodum"), get_card("Feodum")
    state.supply["Silver"] = 20
    # 6 Silvers: Shaman trash -> 9, Hermit trash -> 12 + its own gain = 13.
    p0.hand = [first, get_card("Hermit")]
    p0.discard = [second]
    p0.deck = [get_card("Silver") for _ in range(6)]
    _play(state, "Shaman")
    assert first in p0.hand and not state.trash

    p0.deck = [get_card("Silver") for _ in range(5)]
    _play(state, "Shaman")
    assert first in state.trash

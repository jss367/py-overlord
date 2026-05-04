"""Tests for Renaissance Projects."""

from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.projects import (
    Academy,
    Barracks,
    Capitalism,
    Cathedral,
    CityGate,
    CropRotation,
    Exploration,
    Fair,
    Fleet,
    Guildhall,
    Pageant,
    Piazza,
    Silos,
    SinisterPlot,
    StarChart,
)
from tests.utils import BuyEventAI, DummyAI, TrashFirstAI


def make_state(project, kingdom: str = "Village", n: int = 1):
    ais = [DummyAI() for _ in range(n)]
    state = GameState(players=[])
    state.initialize_game(ais, [get_card(kingdom)], projects=[project])
    return state


def test_cathedral_trashes_card_at_turn_start():
    state = make_state(Cathedral())
    state.players[0].projects.append(state.projects[0])
    p = state.players[0]
    state.current_player_index = 0
    p.hand = [get_card("Copper"), get_card("Estate")]
    p.deck = [get_card("Copper")]
    state.phase = "start"
    state.handle_start_phase()
    assert len(state.trash) == 1


def test_city_gate_draws_then_topdecks():
    state = make_state(CityGate())
    p = state.players[0]
    p.projects.append(state.projects[0])
    state.current_player_index = 0
    p.hand = [get_card("Copper")]
    p.deck = [get_card("Estate"), get_card("Silver")]
    hand_before = len(p.hand)
    state.phase = "start"
    state.handle_start_phase()
    # Drew 1 then topdecked 1 → hand size unchanged (vs drew 1).
    assert len(p.hand) == hand_before
    assert len(p.deck) >= 1


def test_pageant_pays_one_for_coffer():
    state = make_state(Pageant())
    p = state.players[0]
    p.projects.append(state.projects[0])
    p.coins = 3
    p.coin_tokens = 0
    state.current_player_index = 0
    state.phase = "buy"
    state.handle_buy_phase()
    # Pageant fires at end of Buy phase; coins reduced by 1, +1 Coffers.
    assert p.coin_tokens == 1


def test_star_chart_promotes_action_from_discard():
    state = make_state(StarChart())
    p = state.players[0]
    p.projects.append(state.projects[0])
    state.current_player_index = 0
    p.deck = [get_card("Copper")]
    p.discard = [get_card("Village"), get_card("Estate")]
    p.hand = []
    state.phase = "start"
    state.handle_start_phase()
    # The Village should have been moved out of discard.
    assert not any(c.name == "Village" for c in p.discard)


def test_exploration_grants_bonus_when_no_action_treasure_gain():
    state = make_state(Exploration())
    p = state.players[0]
    p.projects.append(state.projects[0])
    p.coin_tokens = 0
    p.villagers = 0
    state.current_player_index = 0
    state.phase = "buy"
    state.handle_buy_phase()
    assert p.coin_tokens == 1
    assert p.villagers == 1


def test_fair_grants_buy_at_turn_start():
    state = make_state(Fair())
    p = state.players[0]
    p.projects.append(state.projects[0])
    state.current_player_index = 0
    p.deck = [get_card("Copper")]
    p.hand = []
    p.buys = 1
    state.phase = "start"
    state.handle_start_phase()
    assert p.buys == 2


def test_silos_discards_coppers_and_redraws():
    state = make_state(Silos())
    p = state.players[0]
    p.projects.append(state.projects[0])
    state.current_player_index = 0
    p.hand = [get_card("Copper"), get_card("Copper"), get_card("Estate")]
    p.deck = [get_card("Silver"), get_card("Gold")]
    state.phase = "start"
    state.handle_start_phase()
    coppers_in_hand = sum(1 for c in p.hand if c.name == "Copper")
    assert coppers_in_hand == 0
    # Should have replaced 2 Coppers with 2 cards.
    assert len(p.hand) == 3


def test_sinister_plot_stockpiles_then_draws():
    state = make_state(SinisterPlot())
    p = state.players[0]
    project = state.projects[0]
    p.projects.append(project)
    state.current_player_index = 0
    p.deck = [get_card("Copper") for _ in range(10)]
    p.hand = []
    state.phase = "start"
    # First 3 turn-starts should stockpile to 3.
    for _ in range(3):
        state.handle_start_phase()
        state.phase = "start"
    assert project.tokens == 3
    # 4th turn-start: remove ALL tokens and +X Cards where X = tokens removed.
    p.hand = []
    state.handle_start_phase()
    assert project.tokens == 0
    assert len(p.hand) >= 3


def test_academy_grants_villager_on_action_gain():
    state = make_state(Academy())
    p = state.players[0]
    p.projects.append(state.projects[0])
    villagers_before = p.villagers
    state.gain_card(p, get_card("Village"))
    assert p.villagers == villagers_before + 1


def test_capitalism_lets_action_play_in_treasure_phase():
    """With Capitalism, a +$ Action is also a Treasure during your turn."""
    from typing import Optional
    from dominion.cards.base_card import Card

    class PlayAllTreasuresAI(DummyAI):
        def choose_treasure(self, state, choices) -> Optional[Card]:
            for c in choices:
                if c is not None:
                    return c
            return None

    ai = PlayAllTreasuresAI()
    state = GameState(players=[])
    state.initialize_game([ai], [get_card("Village")], projects=[Capitalism()])
    p = state.players[0]
    p.projects.append(state.projects[0])
    state.current_player_index = 0
    bazaar = get_card("Bazaar")  # +1 Card +2 Actions +$1
    p.hand = [bazaar]
    p.deck = [get_card("Copper")]
    coins_before = p.coins
    state.phase = "treasure"
    state.handle_treasure_phase()
    assert p.coins > coins_before


def test_fleet_grants_extra_round():
    ais = [DummyAI(), DummyAI()]
    state = GameState(players=[])
    state.initialize_game(ais, [get_card("Village")], projects=[Fleet()])
    p1, p2 = state.players
    p1.projects.append(state.projects[0])
    # Force end-of-game by emptying Provinces.
    state.supply["Province"] = 0
    assert state.is_game_over() is False
    assert state.fleet_extra_round_active
    assert p1 in state.fleet_extra_players
    assert p2 not in state.fleet_extra_players


def test_guildhall_grants_coffers_on_treasure_gain():
    state = make_state(Guildhall())
    p = state.players[0]
    p.projects.append(state.projects[0])
    coffers_before = p.coin_tokens
    state.gain_card(p, get_card("Silver"))
    assert p.coin_tokens == coffers_before + 1


def test_piazza_plays_top_action():
    state = make_state(Piazza())
    p = state.players[0]
    p.projects.append(state.projects[0])
    state.current_player_index = 0
    p.deck = [get_card("Copper"), get_card("Village")]
    p.hand = []
    actions_before = p.actions
    state.phase = "start"
    state.handle_start_phase()
    # Piazza played the Village (top of deck via deck.pop()) → +2 Actions.
    assert p.actions >= actions_before + 2


def test_barracks_adds_action():
    state = make_state(Barracks())
    p = state.players[0]
    p.projects.append(state.projects[0])
    state.current_player_index = 0
    p.deck = [get_card("Copper")]
    p.hand = []
    actions_before = p.actions
    state.phase = "start"
    state.handle_start_phase()
    assert p.actions == actions_before + 1


def test_crop_rotation_discards_victory_for_cards():
    state = make_state(CropRotation())
    p = state.players[0]
    p.projects.append(state.projects[0])
    state.current_player_index = 0
    p.hand = [get_card("Estate"), get_card("Copper")]
    p.deck = [get_card("Silver"), get_card("Gold")]
    state.phase = "start"
    state.handle_start_phase()
    # Estate discarded; +2 Cards drawn.
    assert any(c.name == "Estate" for c in p.discard)
    assert len(p.hand) == 1 + 2  # Copper + 2 drawn

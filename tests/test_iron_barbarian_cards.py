from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.projects import Innovation
from tests.utils import DummyAI


def make_state(num_players=1, kingdom=None, projects=None):
    ais = [DummyAI() for _ in range(num_players)]
    state = GameState(players=[])
    kingdom_cards = kingdom or [get_card("Village")]
    state.initialize_game(ais, kingdom_cards, projects=projects)
    return state


def test_bridge_reduces_cost():
    state = make_state()
    player = state.players[0]
    bridge = get_card("Bridge")
    bridge.on_play(state)
    silver_cost = state.get_card_cost(player, get_card("Silver"))
    assert silver_cost == 2


def test_marauder_gives_spoils_and_ruins():
    state = make_state(num_players=2, kingdom=[get_card("Marauder")])
    player, opponent = state.players
    marauder = get_card("Marauder")
    marauder.on_play(state)
    assert any(card.name == "Spoils" for card in player.hand)
    assert any(card.name == "Ruins" for card in opponent.discard)


def test_innovation_plays_first_gained_action():
    state = make_state(projects=[Innovation()])
    player = state.players[0]
    player.projects.append(Innovation())
    bridge = get_card("Bridge")
    state.supply.setdefault("Bridge", 10)
    state.gain_card(player, bridge)
    assert bridge in player.in_play
    assert bridge not in player.discard
    assert player.innovation_used


def test_tragic_hero_trashes_and_gains_treasure():
    state = make_state()
    player = state.players[0]
    tragic = get_card("Tragic Hero")
    player.hand = [tragic] + [get_card("Copper") for _ in range(7)]
    player.deck = [get_card("Copper") for _ in range(3)]
    player.actions = 1
    player.hand.remove(tragic)
    player.in_play.append(tragic)
    tragic.on_play(state)
    assert any(card.name == "Gold" for card in player.hand)
    assert tragic in state.trash
    assert tragic not in player.in_play


def test_giant_flips_token_and_attacks():
    state = make_state(num_players=2, kingdom=[get_card("Giant")])
    player, opponent = state.players
    opponent.deck = [get_card("Copper")]
    opponent.discard = []
    player.coins = 0
    player.journey_token_face_up = True
    giant = get_card("Giant")
    giant.on_play(state)
    assert player.coins == 1
    assert not player.journey_token_face_up
    giant.on_play(state)
    assert player.coins == 6
    assert player.journey_token_face_up
    assert any(card.name == "Curse" for card in opponent.discard)


def test_barbarian_trashes_and_replaces():
    state = make_state(num_players=2, kingdom=[get_card("Barbarian")])
    player, opponent = state.players
    opponent.deck = [get_card("Silver")]
    opponent.discard = []
    barbarian = get_card("Barbarian")
    barbarian.on_play(state)
    assert any(card.name == "Copper" for card in opponent.discard)
    assert any(card.name == "Silver" for card in state.trash)

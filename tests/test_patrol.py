from dominion.cards.registry import get_card
from dominion.game.game_state import GameState

from tests.utils import ChooseFirstActionAI


class PatrolOrderingAI(ChooseFirstActionAI):
    def order_cards_for_patrol(self, state, player, cards):
        priority = {"Silver": 3, "Village": 2, "Copper": 1}
        return sorted(cards, key=lambda card: priority.get(card.name, 0), reverse=True)


def _setup_state(ai):
    state = GameState(players=[])
    state.initialize_game([ai], [get_card("Patrol")])
    return state, state.players[0]


def test_patrol_moves_victory_and_curse_into_hand_and_orders_deck():
    ai = PatrolOrderingAI()
    state, player = _setup_state(ai)

    player.hand = []
    player.deck = [
        get_card("Gold"),
        get_card("Copper"),
        get_card("Estate"),
        get_card("Silver"),
        get_card("Curse"),
    ]
    player.discard = []

    patrol = get_card("Patrol")
    patrol.play_effect(state)

    assert sorted(card.name for card in player.hand) == ["Curse", "Estate"]
    assert [card.name for card in player.deck] == ["Gold", "Copper", "Silver"]


def test_patrol_shuffles_if_needed_and_respects_ai_order(monkeypatch):
    ai = PatrolOrderingAI()
    state, player = _setup_state(ai)

    player.hand = []
    player.deck = [get_card("Copper"), get_card("Silver")]
    player.discard = [get_card("Curse"), get_card("Estate"), get_card("Village")]

    monkeypatch.setattr("dominion.game.player_state.random.shuffle", lambda seq: None)

    patrol = get_card("Patrol")
    patrol.play_effect(state)

    assert sorted(card.name for card in player.hand) == ["Estate"]
    assert player.discard == []
    assert [card.name for card in player.deck] == ["Curse", "Copper", "Village", "Silver"]

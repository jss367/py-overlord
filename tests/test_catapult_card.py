from dominion.cards.empires.catapult import Catapult
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState
from tests.utils import DummyAI


class CatapultAI(DummyAI):
    def __init__(self, trash_name=None, discard_names=None):
        super().__init__()
        self.trash_name = trash_name
        self.discard_names = discard_names or []
        self.discard_calls = 0
        self.trash_choices = None

    def choose_card_to_trash(self, state, choices):
        self.trash_choices = choices
        if self.trash_name is None:
            return None
        return next((card for card in choices if card.name == self.trash_name), None)

    def choose_cards_to_discard(self, state, player, choices, count, *, reason=None):
        self.discard_calls += 1
        selected = []
        for name in self.discard_names:
            for card in choices:
                if card.name == name and card not in selected:
                    selected.append(card)
                    break
            if len(selected) == count:
                break
        return selected


def make_state(attacker_ai, defender_ai=None):
    defender_ai = defender_ai or CatapultAI()
    players = [PlayerState(attacker_ai), PlayerState(defender_ai)]
    state = GameState(players=players)
    state.setup_supply([])
    state.current_player_index = 0
    for player in players:
        player.hand = []
        player.deck = []
        player.discard = []
        player.in_play = []
        player.duration = []
        player.coins = 0
    return state


def play_catapult(state):
    Catapult().on_play(state)


def test_catapult_trash_is_mandatory_when_ai_returns_none():
    attacker_ai = CatapultAI(trash_name=None)
    state = make_state(attacker_ai)
    attacker, defender = state.players
    attacker.hand = [get_card("Copper")]
    defender.hand = [get_card("Copper") for _ in range(5)]

    play_catapult(state)

    assert [card.name for card in attacker_ai.trash_choices] == ["Copper"]
    assert attacker.hand == []
    assert attacker.coins == 1
    assert [card.name for card in state.trash] == ["Copper"]
    assert len(defender.hand) == 3
    assert len(defender.discard) == 2
    assert not any(card.name == "Curse" for card in defender.discard)


def test_catapult_trashing_copper_gives_coins_but_no_curse():
    state = make_state(CatapultAI(trash_name="Copper"))
    attacker, defender = state.players
    attacker.hand = [get_card("Copper")]
    defender.hand = [get_card("Copper") for _ in range(3)]

    play_catapult(state)

    assert attacker.coins == 1
    assert [card.name for card in state.trash] == ["Copper"]
    assert attacker.hand == []
    assert len(defender.hand) == 3
    assert defender.discard == []


def test_catapult_trashing_silver_curses_and_discards_to_three():
    defender_ai = CatapultAI(discard_names=["Estate", "Duchy"])
    state = make_state(CatapultAI(trash_name="Silver"), defender_ai)
    attacker, defender = state.players
    attacker.hand = [get_card("Silver")]
    defender.hand = [
        get_card("Copper"),
        get_card("Estate"),
        get_card("Silver"),
        get_card("Duchy"),
        get_card("Gold"),
    ]

    play_catapult(state)

    assert attacker.coins == 3
    assert [card.name for card in state.trash] == ["Silver"]
    assert sum(1 for card in defender.discard if card.name == "Curse") == 1
    assert [card.name for card in defender.discard[:2]] == ["Curse", "Estate"]
    assert defender.discard[2].name == "Duchy"
    assert [card.name for card in defender.hand] == ["Copper", "Silver", "Gold"]
    assert defender_ai.discard_calls == 1


def test_catapult_trashing_non_treasure_cost_three_only_curses():
    defender_ai = CatapultAI(discard_names=["Copper", "Estate"])
    state = make_state(CatapultAI(trash_name="Village"), defender_ai)
    attacker, defender = state.players
    attacker.hand = [get_card("Village")]
    defender.hand = [
        get_card("Copper"),
        get_card("Estate"),
        get_card("Silver"),
        get_card("Duchy"),
        get_card("Gold"),
    ]

    play_catapult(state)

    assert attacker.coins == 3
    assert [card.name for card in state.trash] == ["Village"]
    assert sum(1 for card in defender.discard if card.name == "Curse") == 1
    assert len(defender.hand) == 5
    assert defender_ai.discard_calls == 0

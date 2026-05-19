from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState

from tests.utils import DummyAI


class EmpiresChoiceAI(DummyAI):
    def __init__(
        self,
        *,
        trash_name=None,
        archive_names=None,
        discard_names=None,
    ):
        super().__init__()
        self.trash_name = trash_name
        self.archive_names = list(archive_names or [])
        self.discard_names = list(discard_names or [])

    def choose_card_to_trash(self, state, choices):
        if self.trash_name is None:
            return super().choose_card_to_trash(state, choices)
        for card in choices:
            if card.name == self.trash_name:
                return card
        return None

    def choose_archive_card(self, state, player, choices):
        while self.archive_names:
            wanted = self.archive_names.pop(0)
            for card in choices:
                if card.name == wanted:
                    return card
        return super().choose_archive_card(state, player, choices)

    def choose_cards_to_discard(self, state, player, choices, count, *, reason=None):
        picked = []
        for wanted in self.discard_names:
            for card in choices:
                if card.name == wanted and card not in picked:
                    picked.append(card)
                    break
            if len(picked) == count:
                break
        return picked


def _make_game(card_name, ais=None):
    ais = ais or [DummyAI(), DummyAI()]
    state = GameState(players=[PlayerState(ai) for ai in ais])
    state.log_callback = lambda *args, **kwargs: None
    state.initialize_game(ais, [get_card(card_name), get_card("Village")])
    state.log_callback = lambda *args, **kwargs: None
    return state


def test_archive_takes_one_card_now_then_one_each_duration_turn():
    state = _make_game(
        "Archive",
        [EmpiresChoiceAI(archive_names=["Silver", "Gold", "Copper"])],
    )
    player = state.players[0]
    archive = get_card("Archive")
    player.hand = []
    player.deck = [get_card("Copper"), get_card("Silver"), get_card("Gold")]
    player.actions = 0

    archive.on_play(state)

    assert player.actions == 1
    assert [card.name for card in player.hand] == ["Silver"]
    assert [card.name for card in archive.set_aside] == ["Gold", "Copper"]
    assert archive in player.duration
    assert archive.duration_persistent is True

    archive.on_duration(state)
    assert [card.name for card in player.hand] == ["Silver", "Gold"]
    assert [card.name for card in archive.set_aside] == ["Copper"]
    assert archive.duration_persistent is True

    archive.on_duration(state)
    assert [card.name for card in player.hand] == ["Silver", "Gold", "Copper"]
    assert archive.set_aside == []
    assert archive.duration_persistent is False


def test_archive_with_one_card_does_not_stay_in_duration():
    state = _make_game("Archive", [DummyAI()])
    player = state.players[0]
    archive = get_card("Archive")
    player.hand = []
    player.deck = [get_card("Gold")]

    archive.play_effect(state)

    assert [card.name for card in player.hand] == ["Gold"]
    assert archive.set_aside == []
    assert archive not in player.duration
    assert archive.duration_persistent is False


def test_catapult_trashing_treasure_costing_three_or_more_curses_and_discards():
    attacker_ai = EmpiresChoiceAI(trash_name="Silver")
    defender_ai = EmpiresChoiceAI(discard_names=["Gold", "Duchy"])
    state = _make_game("Catapult", [attacker_ai, defender_ai])
    attacker, defender = state.players
    catapult = get_card("Catapult")
    attacker.hand = [get_card("Silver")]
    attacker.coins = 0
    defender.hand = [
        get_card("Estate"),
        get_card("Duchy"),
        get_card("Copper"),
        get_card("Silver"),
        get_card("Gold"),
    ]
    curses_before = state.supply["Curse"]

    catapult.on_play(state)

    assert attacker.coins == 1
    assert [card.name for card in state.trash] == ["Silver"]
    assert state.supply["Curse"] == curses_before - 1
    assert any(card.name == "Curse" for card in defender.discard)
    assert len(defender.hand) == 3
    assert {card.name for card in defender.discard} >= {"Curse", "Gold", "Duchy"}


def test_catapult_trashing_non_treasure_costing_three_or_more_only_curses():
    state = _make_game("Catapult", [EmpiresChoiceAI(trash_name="Village"), DummyAI()])
    attacker, defender = state.players
    catapult = get_card("Catapult")
    attacker.hand = [get_card("Village")]
    defender.hand = [get_card("Copper") for _ in range(5)]
    curses_before = state.supply["Curse"]

    catapult.on_play(state)

    assert state.supply["Curse"] == curses_before - 1
    assert any(card.name == "Curse" for card in defender.discard)
    assert len(defender.hand) == 5


def test_catapult_trashing_cheap_treasure_only_discards():
    state = _make_game("Catapult", [EmpiresChoiceAI(trash_name="Copper"), DummyAI()])
    attacker, defender = state.players
    catapult = get_card("Catapult")
    attacker.hand = [get_card("Copper")]
    defender.hand = [get_card("Copper") for _ in range(5)]
    curses_before = state.supply["Curse"]

    catapult.on_play(state)

    assert state.supply["Curse"] == curses_before
    assert not any(card.name == "Curse" for card in defender.discard)
    assert len(defender.hand) == 3

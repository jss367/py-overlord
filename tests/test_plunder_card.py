from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState

from tests.utils import ChooseFirstActionAI, DummyAI


class StopAfterOneVillageAI(ChooseFirstActionAI):
    """AI that stops First Mate after playing a single copy of the named card."""

    def __init__(self):
        super().__init__()
        self._first_mate_resolution_calls = 0

    def choose_action(self, state, choices):
        non_none = [c for c in choices if c is not None]
        if non_none and all(card.name == "Village" for card in non_none):
            if self._first_mate_resolution_calls == 0:
                self._first_mate_resolution_calls += 1
                return non_none[0]
            return None

        self._first_mate_resolution_calls = 0
        return super().choose_action(state, choices)


class InsigniaChoiceAI(DummyAI):
    def __init__(self, decisions: list[bool]):
        super().__init__()
        self.decisions = list(decisions)
        self.seen_cards: list[str] = []

    def should_topdeck_with_insignia(self, state, player, gained_card):
        self.seen_cards.append(gained_card.name)
        if not self.decisions:
            raise AssertionError("No decision available for Insignia topdeck choice")
        return self.decisions.pop(0)


def _make_state_with_player() -> tuple[GameState, PlayerState]:
    player = PlayerState(DummyAI())
    state = GameState(players=[player])
    return state, player


def test_plunder_gain_also_gains_gold():
    state, player = _make_state_with_player()
    plunder = get_card("Plunder")

    state.supply[plunder.name] = 1
    state.supply["Gold"] = 5

    state.supply[plunder.name] -= 1
    state.gain_card(player, plunder)

    assert any(card.name == "Gold" for card in player.discard)
    assert state.supply["Gold"] == 4


def test_plunder_play_topdecks_gold():
    state, player = _make_state_with_player()
    plunder = get_card("Plunder")

    state.supply["Gold"] = 5
    player.deck = [get_card("Estate")]

    plunder.on_play(state)

    assert player.deck[0].name == "Gold"
    assert len(player.deck) == 2
    assert player.deck[1].name == "Estate"
    assert state.supply["Gold"] == 4


def test_plunder_play_does_nothing_when_gold_empty():
    state, player = _make_state_with_player()
    plunder = get_card("Plunder")

    state.supply["Gold"] = 0
    player.deck = []

    plunder.on_play(state)

    assert player.deck == []
    assert state.supply["Gold"] == 0


def test_trickster_curses_opponents_and_tracks_uses():
    attacker = PlayerState(DummyAI())
    victim = PlayerState(DummyAI())
    state = GameState(players=[attacker, victim])
    state.supply["Curse"] = 10

    trickster = get_card("Trickster")
    trickster.play_effect(state)

    assert attacker.trickster_uses_remaining == 1
    assert any(card.name == "Curse" for card in victim.discard)
    assert state.supply["Curse"] == 9


def test_trickster_sets_aside_treasure_during_cleanup():
    state, player = _make_state_with_player()
    trickster = get_card("Trickster")
    gold = get_card("Gold")
    copper = get_card("Copper")

    state.supply["Curse"] = 10
    player.in_play = [trickster, gold, copper]
    player.trickster_uses_remaining = 1

    state.handle_cleanup_phase()

    assert any(card.name == "Gold" for card in player.hand)
    assert all(card.name != "Gold" for card in player.discard)
    assert player.trickster_uses_remaining == 0


def test_insignia_respects_optional_topdecking():
    ai = InsigniaChoiceAI([True, False, True])
    player = PlayerState(ai)
    state = GameState(players=[player])

    insignia = get_card("Insignia")
    insignia.play_effect(state)

    player.deck = [get_card("Copper")]

    for name in ["Silver", "Estate", "Gold"]:
        state.supply[name] = 1

    state.supply["Silver"] -= 1
    state.gain_card(player, get_card("Silver"))
    assert player.deck[0].name == "Silver"
    assert player.deck[1].name == "Copper"
    assert not any(card.name == "Silver" for card in player.discard)

    state.supply["Estate"] -= 1
    state.gain_card(player, get_card("Estate"))
    assert any(card.name == "Estate" for card in player.discard)

    state.supply["Gold"] -= 1
    state.gain_card(player, get_card("Gold"))
    assert player.deck[0].name == "Gold"
    assert player.deck[1].name == "Silver"
    assert ai.decisions == []
    assert ai.seen_cards == ["Silver", "Estate", "Gold"]


def test_first_mate_effect():
    ai = ChooseFirstActionAI()
    state = GameState(players=[])
    state.initialize_game([ai], [get_card("First Mate"), get_card("Village")])

    player = state.players[0]

    player.hand = [get_card("First Mate"), get_card("Village"), get_card("Village")]
    player.deck = [get_card("Copper") for _ in range(10)]
    player.discard = []
    player.actions = 1

    state.phase = "action"
    state.handle_action_phase()

    assert sum(1 for c in player.in_play if c.name == "Village") == 2
    assert any(c.name == "First Mate" for c in player.in_play)
    assert len(player.hand) == 6


def test_first_mate_can_stop_after_first_copy():
    ai = StopAfterOneVillageAI()
    state = GameState(players=[])
    state.initialize_game([ai], [get_card("First Mate"), get_card("Village")])

    player = state.players[0]

    player.hand = [get_card("First Mate"), get_card("Village"), get_card("Village")]
    player.deck = [get_card("Copper") for _ in range(10)]
    player.discard = []
    player.actions = 1

    state.phase = "action"
    state.handle_action_phase()

    assert sum(1 for c in player.in_play if c.name == "Village") == 1
    assert any(c.name == "Village" for c in player.hand)
    assert len(player.hand) == 6

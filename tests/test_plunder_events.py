"""Tests for the Plunder expansion events."""

from dominion.cards.registry import get_card
from dominion.events.registry import get_event
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState

from tests.utils import ChooseFirstActionAI, DummyAI


class _DiscardFirstAI(DummyAI):
    """Simple AI that always discards/trashes the front of the choices list."""

    def choose_cards_to_discard(self, state, player, choices, count, *, reason=None):
        return list(choices[:count])

    def choose_card_to_trash(self, state, choices):
        for c in choices:
            if c is not None:
                return c
        return None

    def choose_action(self, state, choices):
        for c in choices:
            if c is not None:
                return c
        return None

    def choose_buy(self, state, choices):
        for c in choices:
            if c is not None:
                return c
        return None


def test_bury_topdecks_chosen_card_from_discard():
    player = PlayerState(_DiscardFirstAI())
    state = GameState(players=[player])

    estate = get_card("Estate")
    copper = get_card("Copper")
    player.discard = [estate, copper]
    player.deck = []

    bury = get_event("Bury")
    bury.on_buy(state, player)

    # AI picks first => Estate. It should be on top of deck (at end).
    assert player.deck[-1] is estate
    assert estate not in player.discard


def test_bury_no_op_if_discard_empty():
    player = PlayerState(_DiscardFirstAI())
    state = GameState(players=[player])

    bury = get_event("Bury")
    bury.on_buy(state, player)
    assert player.deck == []


def test_avoid_discards_and_redraws():
    player = PlayerState(_DiscardFirstAI())
    state = GameState(players=[player])

    coppers = [get_card("Copper") for _ in range(5)]
    player.hand = list(coppers)
    player.deck = [get_card("Estate") for _ in range(5)]

    avoid = get_event("Avoid")
    avoid.on_buy(state, player)

    # Discarded 3, drew 3 from deck
    assert len(player.hand) == 5
    assert sum(1 for c in player.discard if c.name == "Copper") == 3


def test_foray_gains_loot_when_3_distinct_names():
    player = PlayerState(_DiscardFirstAI())
    state = GameState(players=[player])

    player.hand = [get_card("Copper"), get_card("Estate"), get_card("Silver")]

    foray = get_event("Foray")
    foray.on_buy(state, player)

    from dominion.cards.plunder.loot_cards import LOOT_CARD_NAMES
    assert any(c.name in LOOT_CARD_NAMES for c in player.discard)


def test_foray_no_loot_when_duplicate_names():
    player = PlayerState(_DiscardFirstAI())
    state = GameState(players=[player])

    player.hand = [get_card("Copper"), get_card("Copper"), get_card("Estate")]

    foray = get_event("Foray")
    foray.on_buy(state, player)

    from dominion.cards.plunder.loot_cards import LOOT_CARD_NAMES
    assert not any(c.name in LOOT_CARD_NAMES for c in player.discard)


def test_peril_trashes_action_for_loot():
    player = PlayerState(_DiscardFirstAI())
    state = GameState(players=[player])
    village = get_card("Village")
    player.hand = [village]

    peril = get_event("Peril")
    peril.on_buy(state, player)

    assert village in state.trash
    from dominion.cards.plunder.loot_cards import LOOT_CARD_NAMES
    assert any(c.name in LOOT_CARD_NAMES for c in player.discard)


def test_peril_no_loot_without_action():
    player = PlayerState(_DiscardFirstAI())
    state = GameState(players=[player])
    player.hand = [get_card("Copper")]

    peril = get_event("Peril")
    peril.on_buy(state, player)

    from dominion.cards.plunder.loot_cards import LOOT_CARD_NAMES
    assert not any(c.name in LOOT_CARD_NAMES for c in player.discard)


def test_scrounge_trashes_estate_for_gold():
    player = PlayerState(_DiscardFirstAI())
    state = GameState(players=[player])
    state.supply["Gold"] = 10
    state.supply["Estate"] = 10

    estate = get_card("Estate")
    player.hand = [estate]

    scrounge = get_event("Scrounge")
    scrounge.on_buy(state, player)

    assert estate in state.trash
    assert any(c.name == "Gold" for c in player.discard)
    assert state.supply["Gold"] == 9


def test_scrounge_gains_estate_when_no_estate_in_hand():
    player = PlayerState(_DiscardFirstAI())
    state = GameState(players=[player])
    state.supply["Gold"] = 10
    state.supply["Estate"] = 10

    scrounge = get_event("Scrounge")
    scrounge.on_buy(state, player)

    assert any(c.name == "Estate" for c in player.discard)
    assert state.supply["Estate"] == 9


def test_prosper_gains_loot_silver_gold():
    player = PlayerState(_DiscardFirstAI())
    state = GameState(players=[player])
    state.supply["Gold"] = 10
    state.supply["Silver"] = 10

    prosper = get_event("Prosper")
    prosper.on_buy(state, player)

    assert any(c.name == "Silver" for c in player.discard)
    assert any(c.name == "Gold" for c in player.discard)
    from dominion.cards.plunder.loot_cards import LOOT_CARD_NAMES
    assert any(c.name in LOOT_CARD_NAMES for c in player.discard)


def test_invasion_gains_action_and_curses_opponents():
    p1 = PlayerState(_DiscardFirstAI())
    p2 = PlayerState(DummyAI())
    state = GameState(players=[p1, p2])
    state.supply["Curse"] = 10
    state.supply["Village"] = 10

    invasion = get_event("Invasion")
    invasion.on_buy(state, p1)

    actions = [c for c in p1.discard if c.is_action]
    assert actions
    assert any(c.name == "Curse" for c in p2.discard)

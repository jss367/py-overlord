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


class _ScroungeTrashAI(_DiscardFirstAI):
    def scrounge_choice(self, state, player, can_gain_estate_from_trash):
        # Default: trash if hand has anything to trash
        return "trash" if player.hand else "gain_estate"


class _ScroungeEstateAI(_DiscardFirstAI):
    def scrounge_choice(self, state, player, can_gain_estate_from_trash):
        return "gain_estate"


def test_scrounge_trash_estate_grants_duchy():
    """Scrounge canonical: Choose: Trash a card from hand; or gain an Estate
    from the trash. If you trashed an Estate, also gain a Duchy.
    """

    player = PlayerState(_ScroungeTrashAI())
    state = GameState(players=[player])
    state.supply["Duchy"] = 10
    state.supply["Estate"] = 10

    estate = get_card("Estate")
    player.hand = [estate]

    scrounge = get_event("Scrounge")
    scrounge.on_buy(state, player)

    assert estate in state.trash
    assert any(c.name == "Duchy" for c in player.discard)
    assert state.supply["Duchy"] == 9


def test_scrounge_trash_non_estate_no_duchy():
    """Trashing a non-Estate card just trashes; no Duchy gain."""

    player = PlayerState(_ScroungeTrashAI())
    state = GameState(players=[player])
    state.supply["Duchy"] = 10
    state.supply["Estate"] = 10

    copper = get_card("Copper")
    player.hand = [copper]

    scrounge = get_event("Scrounge")
    scrounge.on_buy(state, player)

    assert copper in state.trash
    assert not any(c.name == "Duchy" for c in player.discard)


def test_scrounge_gain_estate_from_trash():
    """Scrounge: choose to gain an Estate from the trash."""

    player = PlayerState(_ScroungeEstateAI())
    state = GameState(players=[player])
    state.supply["Estate"] = 10

    # Pre-seed trash with an Estate
    trash_estate = get_card("Estate")
    state.trash.append(trash_estate)

    scrounge = get_event("Scrounge")
    scrounge.on_buy(state, player)

    # The trashed Estate should have moved from trash to player.discard
    assert trash_estate not in state.trash
    assert trash_estate in player.discard


class _ProsperPickAllAI(_DiscardFirstAI):
    def prosper_choose_treasures(self, state, player, available):
        # Take all treasures except Copper
        return [c for c in available if c.name != "Copper"]


def test_prosper_gains_loot_then_chosen_differently_named_treasures():
    """Prosper canonical: gain a Loot, then any number of differently named Treasures."""

    player = PlayerState(_ProsperPickAllAI())
    state = GameState(players=[player])
    state.supply["Copper"] = 10
    state.supply["Silver"] = 10
    state.supply["Gold"] = 10

    prosper = get_event("Prosper")
    prosper.on_buy(state, player)

    from dominion.cards.plunder.loot_cards import LOOT_CARD_NAMES
    assert any(c.name in LOOT_CARD_NAMES for c in player.discard)
    assert any(c.name == "Silver" for c in player.discard)
    assert any(c.name == "Gold" for c in player.discard)
    # AI declined Copper
    assert not any(c.name == "Copper" for c in player.discard)


def test_prosper_only_one_of_each_treasure_name():
    """Prosper gives one of each Treasure name max — not duplicates."""

    player = PlayerState(_ProsperPickAllAI())
    state = GameState(players=[player])
    state.supply["Silver"] = 10
    state.supply["Gold"] = 10

    prosper = get_event("Prosper")
    prosper.on_buy(state, player)

    silvers = sum(1 for c in player.discard if c.name == "Silver")
    golds = sum(1 for c in player.discard if c.name == "Gold")
    assert silvers == 1
    assert golds == 1


def test_invasion_plays_attack_and_gains_duchy_gold_loot_province():
    """Invasion canonical: Play an Attack from hand, gain Duchy + Gold + Loot + Province."""

    class _InvasionAI(_DiscardFirstAI):
        def choose_action(self, state, choices):
            for c in choices:
                if c is not None and c.is_attack:
                    return c
            return None

    p1 = PlayerState(_InvasionAI())
    p2 = PlayerState(DummyAI())
    state = GameState(players=[p1, p2])
    state.supply["Curse"] = 10
    state.supply["Duchy"] = 10
    state.supply["Gold"] = 10
    state.supply["Province"] = 10

    witch = get_card("Witch")
    p1.hand = [witch]

    invasion = get_event("Invasion")
    invasion.on_buy(state, p1)

    # Attack played: Witch → opponents gain Curses
    assert witch in p1.in_play
    assert any(c.name == "Curse" for c in p2.discard)
    # Gained: Duchy, Gold, Loot, Province
    assert any(c.name == "Duchy" for c in p1.discard)
    assert any(c.name == "Gold" for c in p1.discard)
    assert any(c.name == "Province" for c in p1.discard)
    from dominion.cards.plunder.loot_cards import LOOT_CARD_NAMES
    assert any(c.name in LOOT_CARD_NAMES for c in p1.discard)


def test_invasion_no_attack_in_hand_still_gains():
    """Invasion still gains Duchy/Gold/Loot/Province even with no Attack in hand."""

    p1 = PlayerState(_DiscardFirstAI())
    state = GameState(players=[p1])
    state.supply["Duchy"] = 10
    state.supply["Gold"] = 10
    state.supply["Province"] = 10

    invasion = get_event("Invasion")
    invasion.on_buy(state, p1)

    assert any(c.name == "Duchy" for c in p1.discard)
    assert any(c.name == "Gold" for c in p1.discard)
    assert any(c.name == "Province" for c in p1.discard)

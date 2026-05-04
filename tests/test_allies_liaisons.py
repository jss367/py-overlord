"""Tests for Liaison card type and Favor-granting behavior."""

from dominion.cards.base_card import CardType
from dominion.cards.registry import CARD_TYPES, get_card


EXPECTED_LIAISONS = {
    # Wizards
    "Student", "Conjurer", "Sorcerer", "Lich",
    # Townsfolk
    "Town Crier", "Blacksmith", "Miller", "Elder",
    # Clashes
    "Battle Plan", "Archer", "Warlord", "Territory",
    # Standalone
    "Bauble", "Sycophant", "Importer", "Underling",
    "Broker", "Contract", "Emissary", "Galleria",
    "Hunter", "Modify", "Skirmisher", "Specialist", "Swap",
}


def test_liaison_cardtype_exists():
    assert CardType.LIAISON.value == "liaison"


def test_expected_liaisons_have_liaison_type():
    for name in EXPECTED_LIAISONS:
        card = get_card(name)
        assert card.is_liaison, f"{name} should be a Liaison"
        assert CardType.LIAISON in card.types


def test_no_unexpected_liaisons():
    actual = {
        name for name, cls in CARD_TYPES.items()
        if CardType.LIAISON in cls().types
    }
    assert actual == EXPECTED_LIAISONS


def test_underling_grants_favor_when_played():
    from dominion.game.game_state import GameState
    from dominion.game.player_state import PlayerState
    from tests.utils import DummyAI

    player = PlayerState(DummyAI())
    state = GameState(players=[player])
    state.supply = {}

    underling = get_card("Underling")
    player.in_play.append(underling)
    favors_before = player.favors
    underling.on_play(state)
    assert player.favors == favors_before + 1


def test_modify_grants_favor():
    from dominion.game.game_state import GameState
    from dominion.game.player_state import PlayerState
    from tests.utils import DummyAI

    player = PlayerState(DummyAI())
    state = GameState(players=[player])
    state.supply = {"Estate": 1}
    player.hand = [get_card("Copper")]

    modify = get_card("Modify")
    player.in_play.append(modify)
    favors_before = player.favors
    modify.on_play(state)
    assert player.favors == favors_before + 1

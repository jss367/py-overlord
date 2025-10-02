from dominion.cards.base_card import CardType
from dominion.cards.registry import get_card


def test_charm_is_treasure_not_action():
    charm = get_card("Charm")
    assert CardType.TREASURE in charm.types
    assert CardType.ACTION not in charm.types


def test_capital_is_treasure_not_action():
    capital = get_card("Capital")
    assert CardType.TREASURE in capital.types
    assert CardType.ACTION not in capital.types

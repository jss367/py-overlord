from dominion.cards.base_card import CardType
from dominion.cards.registry import CARD_TYPES, get_card

EXPECTED_TREASURE_CARDS = {
    "Amphora",
    "Bank",
    "Cache",
    "Capital",
    "Cauldron",
    "Charm",
    "Collection",
    "Contraband",
    "Copper",
    "Crown",
    "Doubloons",
    "Endless Chalice",
    "Figurehead",
    "Fool's Gold",
    "Fortune",
    "Gold",
    "Hammer",
    "Hoard",
    "Horn of Plenty",
    "Ill-Gotten Gains",
    "Insignia",
    "Jewels",
    "Loan",
    "Masterpiece",
    "Orb",
    "Platinum",
    "Plunder",
    "Prize Goat",
    "Puzzle Box",
    "Quarry",
    "Rocks",
    "Royal Seal",
    "Sextant",
    "Shield",
    "Silver",
    "Spell Scroll",
    "Spoils",
    "Staff",
    "Stash",
    "Sword",
    "Talisman",
    "Venture",
}

MULTI_TYPE_TREASURES = {
    "Amphora": {CardType.TREASURE, CardType.DURATION},
    "Cauldron": {CardType.TREASURE, CardType.ATTACK},
    "Crown": {CardType.ACTION, CardType.TREASURE},
    "Endless Chalice": {CardType.TREASURE, CardType.DURATION},
    "Figurehead": {CardType.TREASURE, CardType.DURATION},
    "Fool's Gold": {CardType.TREASURE, CardType.REACTION},
    "Jewels": {CardType.TREASURE, CardType.DURATION},
    "Rocks": {CardType.TREASURE, CardType.VICTORY},
    "Shield": {CardType.TREASURE, CardType.REACTION},
    "Spell Scroll": {CardType.TREASURE, CardType.ACTION},
    "Sword": {CardType.TREASURE, CardType.ATTACK},
}


def test_registered_treasures_match_expected():
    actual = {
        name
        for name, cls in CARD_TYPES.items()
        if CardType.TREASURE in cls().types
    }
    assert actual == EXPECTED_TREASURE_CARDS


def test_treasure_card_types_are_correct():
    for name in EXPECTED_TREASURE_CARDS:
        card = get_card(name)
        expected_types = MULTI_TYPE_TREASURES.get(name, {CardType.TREASURE})
        assert set(card.types) == expected_types


def test_basic_treasures_have_expected_stats():
    copper = get_card("Copper")
    silver = get_card("Silver")
    gold = get_card("Gold")

    assert copper.cost.coins == 0
    assert copper.stats.coins == 1
    assert copper.starting_supply(None) == 60

    assert silver.cost.coins == 3
    assert silver.stats.coins == 2
    assert silver.starting_supply(None) == 40

    assert gold.cost.coins == 6
    assert gold.stats.coins == 3
    assert gold.starting_supply(None) == 30

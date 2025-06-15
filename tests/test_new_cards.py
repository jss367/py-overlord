from dominion.cards.registry import get_card


def test_new_card_registry():
    names = [
        "Trail",
        "Acting Troupe",
        "Taskmaster",
        "Trader",
        "Torturer",
        "Patrol",
        "Inn",
        "First Mate",
    ]
    for name in names:
        card = get_card(name)
        assert card.name == name

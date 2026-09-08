"""Physical order for named split piles, compatible with Supply counts.

Legacy gainers decrement counts before calling gain_card. Reconcile those
changes at each pile access: a removal takes the topmost matching card and
a return adds a card on top. Rotation never changes the counts.
"""

from collections import Counter


def pile_members(state, name):
    from ..cards.registry import get_card
    from ..cards.split_pile import SplitPileMixin
    from ..cards.empires.castles import CASTLE_ORDER

    card = get_card(name)
    if getattr(card, "pile_order", ()):
        return tuple(card.pile_order)
    if isinstance(card, SplitPileMixin):
        return (
            (card.partner_card_name, name)
            if card.bottom
            else (name, card.partner_card_name)
        )
    if name in CASTLE_ORDER:
        return tuple(CASTLE_ORDER)
    return (name,)


def stack(state, name):
    members = pile_members(state, name)
    if name in state.pile_order:
        return state.pile_order[name]
    stacks = state.ordered_supply_piles
    if members not in stacks:
        stacks[members] = [
            n for n in reversed(members) for _ in range(state.supply.get(n, 0))
        ]
    cards = stacks[members]
    counts = Counter(cards)
    for member in members:
        difference = state.supply.get(member, 0) - counts[member]
        if difference < 0:
            for _ in range(-difference):
                cards.pop(len(cards) - 1 - cards[::-1].index(member))
        elif difference > 0:
            cards.extend([member] * difference)
    return cards


def rotate(state, name):
    cards = stack(state, name)
    if not cards:
        return
    top = cards[-1]
    start = len(cards) - 1
    while start and cards[start - 1] == top:
        start -= 1
    cards[:] = cards[start:] + cards[:start]

"""Mandatory simultaneous hand discards, before any discard reactions."""


def discard_from_hand(state, player, count, reason):
    count = min(count, len(player.hand))
    choices = list(player.hand)
    picks = player.ai.choose_cards_to_discard(
        state, player, choices, count, reason=reason
    )
    selected = []
    for card in list(picks or []) + sorted(
        choices, key=lambda c: (c.is_action or c.is_treasure, c.cost.coins, c.name)
    ):
        if any(card is c for c in choices) and not any(card is c for c in selected):
            selected.append(card)
        if len(selected) == count:
            break
    if not count:
        return []
    for card in selected:
        player.hand.remove(card)
    player.discard.extend(selected)
    for card in selected:
        # A previous reaction can shuffle another selected card away.
        if card in player.discard:
            state._handle_discard_reactions(player, card)
        state._handle_friendly_discard(player, card)
    return selected

"""Way of the Horse — +2 Cards +1 Action. Return this to its pile."""

from .base_way import Way


def _resolve_pile_name(game_state, card) -> str | None:
    """Return the supply pile key that owns ``card``, or ``None`` if the
    card doesn't belong to any active supply pile.

    Most cards' pile key matches ``card.name`` exactly. Mixed-name piles
    represented under a shared key (Knights, Ruins) are resolved via the
    pile_order registry so that e.g. Dame Anna resolves to "Knights"
    instead of looking for a non-existent "Dame Anna" pile.
    """
    name = card.name
    if name in game_state.supply:
        return name
    # Knights pile: ten distinct knight cards share a "Knights" pile.
    if getattr(card, "is_knight", False) and "Knights" in game_state.pile_order:
        return "Knights"
    # Ruins pile: five distinct ruins share a "Ruins" pile.
    if getattr(card, "is_ruins", False) and "Ruins" in game_state.pile_order:
        return "Ruins"
    # Generic fallback: scan pile_order for a pile that contains this name.
    for pile_name, order in game_state.pile_order.items():
        if name in order:
            return pile_name
    return None


class WayOfTheHorse(Way):
    def __init__(self):
        super().__init__("Way of the Horse")

    def apply(self, game_state, card) -> None:
        player = game_state.current_player
        game_state.draw_cards(player, 2)
        player.actions += 1
        # Return the played card to its OWNING supply pile. We resolve the
        # pile by ``card.name`` first (the common case), then by special
        # mixed-name piles (Knights, Ruins) so cards like Dame Anna or
        # Ruined Library are correctly returned to their shared pile and
        # placed back on top. Cards with no resolvable pile (gained from
        # non-Supply zones, etc.) stay in_play to avoid manufacturing a
        # synthetic pile.
        if card not in player.in_play:
            return
        pile_name = _resolve_pile_name(game_state, card)
        if pile_name is None:
            return
        player.in_play.remove(card)
        game_state.supply[pile_name] = game_state.supply.get(pile_name, 0) + 1
        # For ordered mixed-name piles (Knights, Ruins, etc.), put the
        # specific card back on top of the pile_order so the next gain
        # from that pile receives this card.
        if pile_name in game_state.pile_order:
            game_state.pile_order[pile_name].append(card.name)

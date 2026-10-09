"""Legal menus and validated selections for contextual free gains."""

from dominion.ai import tactical_defaults
from dominion.ai.gain_context import FreeGainContext
from dominion.cards.base_card import CardCost
from dominion.cards.registry import get_card


def gained_card_types(state, player, card):
    """Live gain-bonus types, including the active player's Inheritance."""
    action, treasure = state.is_action(card), state.is_treasure(card)
    if state.is_inherited_estate(player, card):
        inherited = get_card(player.inherited_action_name)
        action = True
        treasure = treasure or state.is_treasure(inherited)
    return action, treasure, card.is_victory


def gain_menu(state, player, limit: CardCost):
    choices = []
    seen_piles = set()
    for name, _card, _count in state._iter_gainable_supply_cards():
        pile = state.supply_pile_key(name)
        if pile in seen_piles:
            continue
        seen_piles.add(pile)
        top = state.top_supply_card(pile)
        card = get_card(top) if top is not None else None
        if card is not None and (
            state.get_card_cost(player, card) <= limit.coins
            and card.cost.potions <= limit.potions
            and card.cost.debt <= limit.debt
        ):
            choices.append(card)
    return choices


def resolve_gain(choice, choices):
    """Resolve strategy-created Card objects against the legal menu."""
    return next((c for c in choices if c.name == getattr(choice, "name", None)), None)


def choose_free_gain(state, player, choices, source, sacrificed=None, *, context=None):
    if not choices:
        return None
    context = context or FreeGainContext.build(state, player, source, sacrificed=sacrificed)
    hook = getattr(player.ai, "choose_free_gain", None)
    pick = hook(state, player, list(choices), context) if hook else None
    resolved = resolve_gain(pick, choices)
    if resolved is not None:
        return resolved
    if source in {"Ironworks", "Engineer"}:
        return tactical_defaults.purchase_gain_fallback(choices, source)
    return tactical_defaults.choose_free_gain(state, player, choices, context)


def gain_selected(state, player, card, *, choices=None, source=None, sacrificed=None,
                  destination="discard", context=None, gain_observer=None):
    if card is None:
        return None
    pile = state.supply_pile_key(card.name)
    # Revalidate the exposed member before mutating the physical pile.
    if state.top_supply_card(pile) != card.name:
        return None
    prepare = getattr(player.ai, "prepare_free_gain_record", None)
    commit = None
    if prepare is not None and source is not None and choices is not None:
        context = context or FreeGainContext.build(state, player, source, destination, sacrificed=sacrificed)
        commit = prepare(state, player, choices, card, context)
    gained_identity = []
    def observe(gained):
        gained_identity.append(gained)
        if gain_observer is not None:
            gain_observer(gained)
    kwargs = {"gain_observer": observe} if commit is not None or gain_observer is not None else {}
    actual = state.gain_from_supply(player, card.name, **kwargs)
    if actual is not None and commit is not None:
        commit(gained_identity[0] if gained_identity else actual)
    return actual

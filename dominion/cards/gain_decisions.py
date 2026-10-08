"""Legal menus and validated selections for contextual free gains."""

from dominion.ai import tactical_defaults
from dominion.ai.gain_context import FreeGainContext
from dominion.cards.base_card import CardCost
from dominion.cards.registry import get_card


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


def choose_free_gain(state, player, choices, source, sacrificed=None):
    context = FreeGainContext.build(state, player, source, sacrificed=sacrificed)
    hook = getattr(player.ai, "choose_free_gain", None)
    pick = hook(state, player, list(choices), context) if hook else None
    return resolve_gain(pick, choices) or tactical_defaults.choose_free_gain(
        state, player, choices, context
    )


def gain_selected(state, player, card, *, choices=None, source=None, sacrificed=None, destination="discard"):
    if card is None:
        return None
    pile = state.supply_pile_key(card.name)
    # Revalidate the exposed member before mutating the physical pile.
    if state.top_supply_card(pile) != card.name:
        return None
    prepare = getattr(player.ai, "prepare_free_gain_record", None)
    commit = None
    if prepare is not None and source is not None and choices is not None:
        context = FreeGainContext.build(state, player, source, destination, sacrificed=sacrificed)
        commit = prepare(state, player, choices, card, context)
    gained = state.take_top_supply_card(pile)
    actual = state.gain_card(player, gained) if gained is not None else None
    if actual is not None and commit is not None:
        commit(actual)
    return actual

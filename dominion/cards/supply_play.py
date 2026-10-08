"""Legal menus and mandatory fallback for Command supply plays.

Playing a Supply card is neither buying nor gaining it: purchase restrictions
such as Grand Market's Copper rule do not constrain this menu.
"""

from dominion.ai import tactical_defaults


def supply_action_choices(state, player, max_cost, *, allow_duration=True):
    from dominion.cards.registry import get_card

    choices = []
    seen = set()
    for pile, count in state.supply.items():
        if count <= 0 or pile in state.non_supply_pile_names:
            continue
        if state._is_ferryman_reserved_pile_name(pile):
            continue
        try:
            name = state.top_supply_card(pile)
            card = get_card(name) if name else None
        except ValueError:
            continue
        if card is None or card.name in seen:
            continue
        seen.add(card.name)
        if (
            state.is_action(card)
            and not card.is_command
            and (allow_duration or not card.is_duration)
            and not card.cost.potions
            and not card.cost.debt
            and state.get_card_cost(player, card) <= max_cost
        ):
            choices.append(card)
    return choices


def select_supply_action(state, player, choices, hook_name, *, legacy_action=False):
    """Resolve a mandatory selection against the legal menu, never Supply order."""
    if not choices:
        return None
    hook = getattr(player.ai, hook_name, None)
    choice = hook(state, player, choices) if hook else None
    if hook is None and legacy_action:
        choice = player.ai.choose_action(state, choices + [None])
    name = getattr(choice, "name", None)
    legal = next((card for card in choices if card.name == name), None)
    return legal or tactical_defaults.choose_supply_action_target(state, player, choices)

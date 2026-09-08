"""Shared legal choices and gains for Allies cards and landscapes."""

from ..base_card import Card, CardCost


def decide(state, player, reason, options, default):
    """An overridable decision, with a legal deterministic fallback."""
    default = default if default in options else options[0]
    hook = getattr(player.ai, "choose_allies_option", None)
    choice = hook(state, player, reason, list(options), default) if hook else default
    return choice if choice in options else default


def select_modes(state, player, card, options, defaults, count=1):
    """Choose distinct printed modes, including Elder's optional extra choices."""
    # Elder applies whenever this card offers abilities this turn, including
    # both separate choose clauses on Count; it is not a consumable allowance.
    extra = getattr(player, "elder_choices", {}).get(card, 0)
    maximum = min(len(options), count + extra)
    defaults = list(dict.fromkeys([o for o in defaults if o in options] + options))[
        :maximum
    ]
    hook = getattr(player.ai, "choose_card_modes", None)
    chosen = (
        hook(state, player, card, list(options), count, maximum, defaults)
        if hook
        else defaults
    )
    selected = []
    for option in chosen or []:
        if option in options and option not in selected and len(selected) < maximum:
            selected.append(option)
    for option in defaults:
        if len(selected) >= min(count, len(options)):
            break
        if option not in selected:
            selected.append(option)
    return [option for option in options if option in selected]


def effective_cost(state, card):
    return CardCost(
        state.get_card_cost(state.turn_player, card), card.cost.potions, card.cost.debt
    )


def at_most(cost, limit):
    return all(
        a <= b for a, b in zip(cost.comparison_tuple(), limit.comparison_tuple())
    )


def cheaper(cost, limit):
    return at_most(cost, limit) and cost != limit


def candidates(state, limit=None, predicate=lambda c: True):
    from ..registry import get_card

    choices = []
    for name, count in list(state.supply.items()):
        if count <= 0 or name in state.non_supply_pile_names:
            continue
        pile_card = get_card(name)
        order = state.pile_order.get(name)
        if name in state.pile_order:
            if not order or not Card.may_be_bought(pile_card, state):
                continue
        elif not pile_card.may_be_gained(state):
            continue
        card = get_card(order[-1]) if order else pile_card
        if predicate(card) and (
            limit is None or at_most(effective_cost(state, card), limit)
        ):
            choices.append(card)
    return choices


def choose_gain(state, player, choices):
    if not choices:
        return None
    old_index, old_turn = state.current_player_index, state.reaction_turn_player_index
    state.reaction_turn_player_index = state.players.index(state.turn_player)
    state.current_player_index = state.players.index(player)
    try:
        choice = player.ai.choose_buy(state, choices + [None])
    finally:
        state.current_player_index, state.reaction_turn_player_index = (
            old_index,
            old_turn,
        )
    if choice not in choices:
        choice = max(choices, key=lambda c: (effective_cost(state, c).coins, c.name))
    return choice


def gain(state, player, choices, *, to_deck=False, to_hand=False):
    choice = choose_gain(state, player, choices)
    if choice is None:
        return None
    pile = state._resolve_changeling_pile_name(choice)
    if pile is None or state.supply.get(pile, 0) <= 0:
        return None
    state.supply[pile] -= 1
    if pile in state.pile_order:
        state.pile_order[pile].pop()
    return state.gain_card(player, choice, to_deck=to_deck, to_hand=to_hand)


def trash_from_hand(state, player, choices=None, mandatory=True):
    choices = list(player.hand if choices is None else choices)
    if not choices:
        return None
    choice = player.ai.choose_card_to_trash(state, choices)
    if choice not in choices:
        if not mandatory:
            return None
        choice = min(
            choices,
            key=lambda c: (c.name != "Curse", effective_cost(state, c).coins, c.name),
        )
    player.hand.remove(choice)
    state.trash_card(player, choice)
    return choice


def discard(state, player, count, reason):
    choices = list(player.hand)
    count = min(count, len(choices))
    picks = player.ai.choose_cards_to_discard(
        state, player, choices, count, reason=reason
    )
    selected = []
    for card in list(picks or []) + choices:
        if card in choices and card not in selected and len(selected) < count:
            selected.append(card)
    # Remove the whole selection before reactions can draw or play any of it.
    for card in selected:
        player.hand.remove(card)
    for card in selected:
        state.discard_card(player, card)
    return len(selected)


def rotate(state, player, pile):
    options = state.rotatable_supply_piles() if pile is None else [pile]
    chosen = decide(state, player, "rotate_pile", [None] + options, None)
    if chosen is not None:
        state.rotate_supply_pile(chosen)


def play_from_hand(state, player, *, treasures=False):
    choices = [
        c for c in player.hand if c.is_action or (treasures and state.is_treasure(c))
    ]
    if not choices or not state._voyage_can_play_from_hand(player):
        return None
    default = player.ai.choose_action(
        state, [c for c in choices if c.is_action] + [None]
    )
    if default is None and treasures:
        default = player.ai.choose_treasure(
            state, [c for c in choices if state.is_treasure(c)] + [None]
        )
    choice = decide(state, player, "play_from_hand", [None] + choices, default)
    if choice is None or not state.move_card_from_hand_to_play(player, choice):
        return None
    if choice.is_action:
        if not state.play_action_indirectly(
            player, choice, blocked_return_zone=player.hand
        ):
            return None
    else:
        state.play_treasure_indirectly(player, choice)
    return choice


def retain_multiplier(player, multiplier, target):
    if (
        target in player.duration
        or target in player.multiplied_durations
        or getattr(target, "duration_targets", [])
    ) and multiplier in player.in_play:
        targets = getattr(multiplier, "duration_targets", [])
        if target not in targets:
            targets.append(target)
        multiplier.duration_targets = targets


def plus_cards(state, player, count):
    from ...ways.chameleon import chameleon_plus_cards

    chameleon_plus_cards(state, player, count)


def plus_coins(player, count):
    from ...ways.chameleon import chameleon_plus_coins

    chameleon_plus_coins(player, count)

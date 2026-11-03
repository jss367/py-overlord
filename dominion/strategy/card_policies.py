"""Bounded, serializable tactical policy families for strategy search."""

from copy import deepcopy
import json

# Each vocabulary is deliberately finite; None inherits, {} declares no overrides.
POLICY_DOMAINS = {
    'watchtower': {'keep_copper_below_income': (0, 3, 5), 'topdeck_min_cost': (3, 4, 5),
                  'terminal_limit': (2, 4, 6), 'topdeck_hand_limit': (3, 5, 8)},
    'clerk': {'dead_cards_first': (False, True), 'play_at_start': (False, True)},
    'investment': {'min_names': (2, 3, 4), 'duplicate_name_discount': (False, True), 'closing_names': (1, 2, 3),
                   'closing_provinces': (0, 1, 2), 'preserve_buy_breakpoint': (False, True),
                   'future_junk_keep': (0, 2, 4), 'excess_copy_cashout': (2, 3, 4)},
    'bounty_hunter': {'prefer_new_name': (False, True), 'buy_breakpoint': (5, 6, 8, 11),
                     'keep_good_copies': (0, 1, 2)},
    'gain_order': {'first': ('sleigh', 'sheepdog', 'cargo_ship')},
}
FAMILY_CARDS = {'watchtower': {'Watchtower'}, 'clerk': {'Clerk'},
                'investment': {'Investment'}, 'bounty_hunter': {'Bounty Hunter'},
                'gain_order': {'Sleigh', 'Sheepdog', 'Cargo Ship'}}


def validate_policies(policies):
    if policies is None:
        return None
    if not isinstance(policies, dict):
        raise ValueError('Card policies must be a mapping or None')
    for family, values in policies.items():
        if family not in POLICY_DOMAINS or not isinstance(values, dict):
            raise ValueError(f'Unknown card policy family: {family}')
        for name, value in values.items():
            domain = POLICY_DOMAINS[family].get(name, ())
            if not any(type(value) is type(v) and value == v for v in domain):
                raise ValueError(f'Invalid card policy parameter: {family}.{name}')
    return deepcopy(policies)


def policy(strategy, family):
    settings = getattr(strategy, 'card_decision_policies', None)
    if settings is None:
        return {}
    # Reject malformed loaded/exported settings before they affect a decision.
    return validate_policies(settings).get(family, {})


def policy_signature(strategy):
    settings = validate_policies(getattr(strategy, 'card_decision_policies', None))
    return None if settings is None else json.dumps(settings, sort_keys=True, separators=(',', ':'))


def mutate_policies(strategy, kingdom, rate, rng):
    available = [f for f, cards in FAMILY_CARDS.items() if cards & set(kingdom)]
    if not available or rate <= 0 or rng.random() >= rate:
        return
    settings = validate_policies(getattr(strategy, 'card_decision_policies', None))
    settings = settings if settings is not None else {}
    family = rng.choice(available)
    if family in settings and rng.random() < .15:
        del settings[family]
    else:
        values = settings.setdefault(family, {})
        name = rng.choice(list(POLICY_DOMAINS[family]))
        choices = [v for v in POLICY_DOMAINS[family][name] if v != values.get(name)]
        values[name] = rng.choice(choices)
    strategy.card_decision_policies = settings


def crossover_policies(child, a, b, rng):
    if getattr(a, 'card_decision_policies', None) is not None or getattr(b, 'card_decision_policies', None) is not None:
        if rng.random() < .5:
            child.card_decision_policies = validate_policies(getattr(b, 'card_decision_policies', None))
    if getattr(child, '_strategic_genome', None) is not None:
        child._strategic_genome.card_decision_policies = deepcopy(child.card_decision_policies)


def investment_treasures(state, player):
    if state is None:
        return [c for c in player.hand if c.is_treasure]
    from dominion.cards.gain_decisions import live_treasures
    return live_treasures(state, player, player.hand)


def investment_points(state, player):
    """The self-trash mode scores every remaining live Treasure name."""
    return len({card.name for card in investment_treasures(state, player)})


def investment_mode(strategy, state, player, can_trash_this):
    if not can_trash_this:
        return 'coin'
    settings = policy(strategy, 'investment')
    threshold = settings.get('min_names', 3)
    pile = 'Colony' if state is not None and 'Colony' in state.supply else 'Province'
    closing = state is not None and settings.get('closing_provinces', 0) and state.supply.get(pile, 8) <= settings['closing_provinces']
    excessive = bool(settings.get('excess_copy_cashout')) and player.count('Investment') >= settings['excess_copy_cashout']
    if closing or excessive:
        threshold = settings.get('closing_names', 2)
    junk = sum(c.name in {'Curse','Copper','Estate'} for c in player.all_cards())
    if settings.get('future_junk_keep', 0) and junk >= settings['future_junk_keep'] and not (closing or excessive):
        return 'coin'
    treasures = investment_treasures(state, player)
    if treasures and not (closing or excessive) and settings.get('duplicate_name_discount', True):
        weakest = next((c for c in treasures if c.name == 'Copper'), min(treasures, key=lambda c: (c.cost.coins, c.name)))
        if sum(c.name == weakest.name for c in treasures) > 1:
            threshold -= 1
    points = investment_points(state, player)
    if settings.get('preserve_buy_breakpoint', False):
        income = player.coins + sum(c.stats.coins for c in investment_treasures(state, player))
        if any(income < price <= income + 1 for price in (5, 6, 8, 11)):
            return 'coin'
    return 'trash' if points >= threshold else 'coin'

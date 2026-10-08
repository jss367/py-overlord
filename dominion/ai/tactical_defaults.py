"""Shared tactical baselines for AIs and strategy-specific overrides.

These rank an already legal menu; card effects remain responsible for legality.
They are intentionally modest heuristics, not claims of optimal card play.
"""

from dominion.cards.base_card import Card


def choose_courier_target(player, choices: list[Card]) -> Card | None:
    """Rank free discard plays by chaining, needed Actions, draw, and money.

    Chain another Courier while a deck remains: it adds money and can still
    select the original target. With no deck it would shuffle that target
    away, so compare its printed resources normally. Complex card effects
    are deliberately left to strategy overrides.
    """
    terminals = sum(c.is_action and c.stats.actions == 0 for c in player.hand)
    missing_actions = max(0, terminals - player.actions)

    def score(card: Card) -> tuple:
        drawable = len(player.deck) + sum(c is not card for c in player.discard)
        draw = min(card.stats.cards, drawable)
        return (
            card.name == "Courier" and bool(player.deck),
            min(card.stats.actions, missing_actions),
            draw * 2 + card.stats.coins,
            card.stats.buys,
            card.cost.coins,
            card.name,
        )

    return max(choices, key=score, default=None)


def choose_overlord_target(player, choices: list[Card]) -> Card | None:
    """Prefer action support when needed, otherwise immediate draw and money."""
    terminals = sum(c.is_action and c.stats.actions == 0 for c in player.hand)
    needs_actions = terminals > player.actions

    def score(card: Card) -> tuple:
        return (
            needs_actions and card.stats.actions >= 2,
            card.stats.cards * 2 + card.stats.coins,
            card.stats.actions,
            card.stats.buys,
            card.cost.coins,
            card.name,
        )

    return max(choices, key=score, default=None)


def choose_quartermaster_gain(choices: list[Card]) -> Card | None:
    """Prefer non-Victory, non-junk gains, then cost and printed resources."""
    return max(
        choices,
        key=lambda c: (
            c.name not in {"Curse", "Copper"} and not c.is_ruins,
            not c.is_victory,
            c.cost.coins,
            c.stats.cards,
            c.stats.actions,
            c.stats.coins,
            c.name,
        ),
        default=None,
    )


def quartermaster_take_all(mat: list[Card]) -> bool:
    """Baseline collection cadence: gain twice, then collect; overridable."""
    return len(mat) >= 2


def discard_priority(card: Card) -> tuple:
    """Prefer dead cards, then cheap economy, preserving live green hybrids."""
    dead = card.name == "Curse" or (
        card.is_victory and not card.is_action and not card.is_treasure
    )
    return (not dead, card.name != "Curse", card.name != "Copper", card.cost.coins, card.name)


def choose_next_turn_cards(state, player, choices: list[Card], count: int) -> list[Card]:
    """Optional storage: stranded Actions, then money above a buy breakpoint.

    Printed resources estimate usefulness, not special card effects. Do not
    store dead cards: returning them adds no value to the next hand. Preserve
    affordable supply-cost breakpoints and a minimum $3 building hand.
    """
    if not choices or count <= 0:
        return []

    from dominion.cards.registry import get_card

    hand = list(player.hand)
    money = player.coins + sum(c.stats.coins for c in hand if c.is_treasure)
    costs = [3]
    for name, remaining in state.supply.items():
        if remaining <= 0 or name in state.non_supply_pile_names:
            continue
        card = get_card(name)
        if card.cost.debt == 0 and card.cost.potions == 0:
            costs.append(state.get_card_cost(player, card))
    floor = max((cost for cost in costs if cost <= money), default=money)
    # There may be no next turn when buying the final Province/Colony.
    if any(state.supply.get(name) == 1 and money >= state.get_card_cost(player, get_card(name))
           for name in ("Province", "Colony")):
        return []

    def next_value(card):
        return (card.stats.cards * 2 + card.stats.coins, card.cost.coins, card.name)

    terminals = sorted(
        (c for c in hand if c.is_action and c.stats.actions == 0),
        key=next_value, reverse=True,
    )
    # A Village or cantrip must remain usable this turn; account for its support.
    action_budget = player.actions + player.villagers
    if action_budget > 0:
        action_budget += sum(max(0, c.stats.actions - 1) for c in hand if c.is_action)
    stranded = (
        [c for c in hand if c.is_action] if action_budget <= 0 else terminals[action_budget:]
    )
    selected = []
    for card in sorted(stranded, key=next_value, reverse=True):
        if any(card is c for c in choices) and len(selected) < max(0, count):
            selected.append(card)
    for card in sorted((c for c in choices if c.is_treasure and not c.is_action),
                       key=next_value, reverse=True):
        if len(selected) >= max(0, count):
            break
        value = card.stats.coins
        if value > 0 and money - value >= floor:
            selected.append(card)
            money -= value
    return selected

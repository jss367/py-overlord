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


def choose_supply_action_target(state, player, choices: list[Card]) -> Card | None:
    """Rank a legal mandatory supply play, independently of hand play order.

    Prioritize needed Actions, then usable draw/money, attack pressure, junk
    removal and discounted next-turn resources. Named effects below are a
    small audited set, not a general interpreter of card text. Unknown effects
    use printed resources; strategies can override each Command's decision.
    """
    terminals = sum(c.is_action and c.stats.actions == 0 for c in player.hand)
    needs_actions = terminals > player.actions
    drawable = len(player.deck) + len(player.discard)
    opponents = [p for p in state.players if p is not player] if state else []
    provinces = state.supply.get("Province", 8) if state else 8
    junk = sum(
        c.name == "Curse" or (c.name in {"Estate", "Hovel", "Overgrown Estate"} and provinces > 2)
        or c.is_ruins
        for c in player.hand
    )
    # Avoid treating the starting economy as disposable. Only surplus Coppers
    # with at least $3 in other printed Treasure income are trashing fuel.
    other_money = sum(c.stats.coins for c in player.all_cards() if c.is_treasure and c.name != "Copper")
    if other_money >= 3:
        junk += sum(c.name == "Copper" for c in player.hand)

    trash_capacity = {"Chapel": 4, "Steward": 2, "Junk Dealer": 1}
    # (immediate draw, immediate money, immediate buys, future resource value).
    durations = {
        "Caravan": (1, 0, 0, 2),
        "Fishing Village": (0, 1, 0, 2),
        "Wharf": (2, 0, 1, 4),
        "Merchant Ship": (0, 2, 0, 2),
        "Lighthouse": (0, 1, 0, 1),
    }

    def score(card: Card) -> tuple:
        draw, money, buys, future = durations.get(
            card.name, (card.stats.cards, card.stats.coins, card.stats.buys, 0)
        )
        if card.name == "Steward":
            draw, money = (2, 0) if drawable >= 2 else (0, 2)
        value = min(draw, drawable) * 2 + money
        if card.is_attack and opponents:
            attack = 4
            if card.name == "Militia":
                attack = 2 * max(max(0, len(p.hand) - 3) for p in opponents)
            elif card.name in {"Witch", "Sea Hag", "Familiar"}:
                attack = 4 if state.supply.get("Curse", 0) else 0
            value += attack
        if card.name in trash_capacity:
            # Steward's trashing mode replaces its draw/money, not adds to it.
            trash_value = min(junk, trash_capacity[card.name]) * 3
            value = max(value, trash_value) if card.name == "Steward" else value + trash_value
            if card.name == "Junk Dealer" and not junk:
                value -= 4  # Mandatory trash can destroy useful economy.
        value += future * 0.75 if provinces > 2 else 0
        if card.name == "Pillage":
            value = -1  # A virtual card cannot trash itself for its payoff.
        return (
            needs_actions and card.stats.actions >= 2,
            value,
            card.stats.actions,
            buys,
            card.cost.coins,
            card.name,
        )

    return max(choices, key=score, default=None)


def choose_overlord_target(player, choices: list[Card], *, state=None) -> Card | None:
    """Compatibility entry point for the shared supply-play baseline."""
    return choose_supply_action_target(state, player, choices)


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
    money = player.coins + sum(c.stats.coins for c in hand if state.is_treasure(c))
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

    # No Actions does not strand cards still playable as Treasures or at Night.
    # Use the live Treasure type so Capitalism is covered as well as Crown.
    action_only = [
        c for c in hand if c.is_action and not state.is_treasure(c) and not c.is_night
    ]
    terminals = sorted(
        (c for c in action_only if c.stats.actions == 0),
        key=next_value, reverse=True,
    )
    # A Village or cantrip must remain usable this turn; account for its support.
    action_budget = player.actions + player.villagers
    if action_budget > 0:
        action_budget += sum(max(0, c.stats.actions - 1) for c in hand if c.is_action)
    stranded = (
        action_only if action_budget <= 0 else terminals[action_budget:]
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

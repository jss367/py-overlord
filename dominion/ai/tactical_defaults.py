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
        if card.name in {"Pillage", "Feast"}:
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

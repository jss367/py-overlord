"""Shared tactical baselines for AIs and strategy-specific overrides.

These rank an already legal menu; card effects remain responsible for legality.
They are intentionally modest heuristics, not claims of optimal card play.
"""

from dominion.cards.base_card import Card
from dominion.ai.gain_context import FreeGainContext


def free_gain_value(state, player, card, context: FreeGainContext) -> float:
    """Modest deck value, with diminishing returns and late-game points.

    This deliberately uses printed resources; special engines should supply
    priorities or a contextual override. Ownership includes stored cards.
    """
    if card is None:
        return 0
    if card.name == "Curse" or card.is_ruins:
        return -8
    if card.name == "Copper":
        return -1
    points = card.get_victory_points(player)
    pure_victory = card.is_victory and not card.is_action and not card.is_treasure
    if pure_victory:
        return points * 4 if context.endgame else -2
    owned = context.owned_counts.get(card.name, 0)
    value = card.stats.cards * 2 + card.stats.coins * 2 + card.stats.actions * .5
    value += state.get_card_cost(player, card) * .1
    if card.is_action:
        cards = [c for c in player.all_cards() if c is not context.sacrificed]
        terminals = sum(c.is_action and c.stats.actions == 0 for c in cards)
        villages = sum(max(0, c.stats.actions - 1) for c in cards)
        if card.stats.actions == 0:
            value -= max(0, terminals - villages - 1) * 2
        elif card.stats.actions >= 2:
            value += min(2, max(0, terminals - villages)) * 2
        value -= owned * 1.5
    if context.destination == "hand":
        value += hand_card_value(player, card)
    if context.endgame:
        value += max(0, points) * 4
    return value


def choose_free_gain(state, player, choices, context):
    return max(choices, key=lambda c: (
        free_gain_value(state, player, c, context), c.cost.coins, c.name
    ), default=None)


def hand_card_value(player, card):
    """Immediate printed utility, penalizing Actions that cannot be played."""
    if card.is_action:
        terminals = sum(c.is_action and c.stats.actions == 0 for c in player.hand)
        if card.stats.actions >= 2:
            return card.stats.cards * 2 + max(0, terminals - player.actions) * 3
        if player.actions <= terminals and card.stats.actions == 0:
            return 0
        return card.stats.cards * 2 + card.stats.coins * 2
    if card.is_treasure:
        return card.stats.coins * 2
    return 0


def choose_remodel_option(state, player, options, choose_gain):
    """Compare complete trash/gain pairs, including mandatory bad gains."""
    pairs = []
    for trashed, choices in options:
        context = FreeGainContext.build(state, player, "Remodel", sacrificed=trashed)
        gain = choose_gain(state, player, choices, context)
        gain = next((c for c in choices if c.name == getattr(gain, "name", None)), None)
        if gain is None:
            gain = choose_free_gain(state, player, choices, context)
        # Retaining a junk card has negative value; losing useful economy is
        # expensive. Preserve Victory points near the end unless upgrading.
        keep_context = FreeGainContext.build(state, player, "Remodel")
        delta = free_gain_value(state, player, gain, context) - free_gain_value(
            state, player, trashed, keep_context
        )
        pairs.append((delta, trashed, gain))
    best = max(pairs, key=lambda p: (p[0], p[1].name), default=None)
    return (best[1], best[2]) if best else (None, None)


def choose_anvil_option(state, player, treasures, target):
    """Spend a Treasure only when the gain outweighs this turn's lost money."""
    context = FreeGainContext.build(state, player, "Anvil")
    if target is None or not treasures:
        return None, None
    treasure = min(treasures, key=lambda c: (hand_card_value(player, c), c.name))
    if free_gain_value(state, player, target, context) <= hand_card_value(player, treasure):
        return None, None
    return treasure, target


def choose_quartermaster_card(player, mat):
    return max(mat, key=lambda c: (hand_card_value(player, c), c.cost.coins, c.name), default=None)


def quartermaster_should_collect(state, player, mat):
    """Use a useful stored card promptly; points already count on the mat."""
    from dominion.cards.base_card import CardCost
    from dominion.cards.gain_decisions import gain_menu

    pick = choose_quartermaster_card(player, mat)
    if pick is None:
        return False
    context = FreeGainContext.build(state, player, "Quartermaster", "quartermaster")
    gains = gain_menu(state, player, CardCost(coins=4))
    gain = choose_free_gain(state, player, gains, context)
    value = free_gain_value(state, player, gain, context)
    immediate = hand_card_value(player, pick)
    if gain is None or value <= 0:
        return True  # Taking even a dead card avoids a mandatory junk gain.
    if context.endgame and gain.get_victory_points(player) > 0:
        return immediate > value
    return immediate > 0


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

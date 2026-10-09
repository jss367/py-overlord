"""Shared tactical baselines for AIs and strategy-specific overrides.

These rank an already legal menu; card effects remain responsible for legality.
They are intentionally modest heuristics, not claims of optimal card play.
"""

from dominion.cards.base_card import Card
from dominion.ai.gain_context import FreeGainContext


def _deck_gain_value(state, player, card, context: FreeGainContext) -> float:
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


def free_gain_value(state, player, card, context: FreeGainContext) -> float:
    """Deck value plus Ironworks' immediate live-type bonuses when applicable."""
    value = _deck_gain_value(state, player, card, context)
    if card is None or context.source != "Ironworks":
        return value
    from dominion.cards.gain_decisions import gained_card_types

    action, treasure, victory = gained_card_types(state, player, card)
    if action and not player.ignore_action_bonuses:
        stranded = player.actions == 0 and any(
            state.is_action(c) or state.is_inherited_estate(player, c) for c in context.hand
        )
        value += 3 if stranded else .5
    if treasure:
        value += 2
    if victory:
        value += 2
    return value


def purchase_gain_fallback(choices, source):
    """Preserve the two gainers' mandatory fallback when purchases select nothing."""
    if source == "Ironworks":
        key = lambda c: (c.cost.coins, c.is_action, c.is_treasure, c.is_victory, c.name)
    else:
        key = lambda c: (c.cost.coins, c.name)
    return max(choices, key=key, default=None)


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


def guaranteed_play_resources(state, player, card, *, followups=True, harbor_pending=0, coins_before=None, inner_coins=0, harbor_after_followups=False):
    """Known external +Coins/+Actions; never run hooks or inspect future draws."""
    coins = int(state.has_pile_token(player, card.name, "+$1"))
    actions = int(state.has_pile_token(player, card.name, "+1 Action"))
    if state.is_action(card):
        actions += player.champions_in_play
    if followups:
        # Harbor checks coins before legacy Training/Prophecy/Ally hooks.
        if not harbor_after_followups and coins_before is not None and player.coins + coins + inner_coins > coins_before:
            coins += harbor_pending
        training = getattr(player, "training_pile", None)
        if training and state.supply_pile_key(card.name) == state.supply_pile_key(training):
            coins += 1
        prophecy = state.prophecy
        if prophecy is not None and prophecy.is_active:
            if prophecy.name == "Great Leader" and state.is_action(card):
                actions += 1
            if prophecy.name == "Approaching Army" and card.is_attack:
                coins += 1
        if card.is_liaison:
            for ally in state.allies:
                if ally.name == "League of Shopkeepers":
                    coins += int(player.favors >= 5)
                    actions += int(player.favors >= 10 and not player.ignore_action_bonuses)
        if harbor_after_followups and coins_before is not None and player.coins + coins + inner_coins > coins_before:
            coins += harbor_pending
    return coins, actions


def choose_next_turn_cards(state, player, choices: list[Card], count: int) -> list[Card]:
    """Optional storage: stranded Actions, then money above a buy breakpoint.

    Printed resources estimate usefulness, not special card effects. Do not
    store dead cards: returning them adds no value to the next hand. Preserve
    affordable supply-cost breakpoints and a minimum $3 building hand.
    """
    if not choices or count <= 0:
        return []

    hand = list(player.hand)
    # Ordinary hand plays belong to this player's turn. Indirect plays (for
    # example Toil/March in Buy) do not reopen earlier play phases.
    own_turn = player is state.turn_player
    actions_playable = own_turn and state.phase in {"start", "action"}
    treasures_playable = own_turn and state.phase in {"start", "action", "treasure"}
    night_playable = own_turn and state.phase in {"start", "action", "treasure", "buy", "night"}
    buys_available = own_turn and player.buys > 0 and state.phase in {"start", "action", "treasure", "buy"}

    def treasure_income(card):
        if not treasures_playable or not state.is_treasure(card):
            return 0
        return card.stats.coins + guaranteed_play_resources(state, player, card)[0]

    pending = getattr(state, "_pending_play_context", None)
    pending_coins, pending_actions = (0, 0)
    while pending is not None:
        if pending["player"] is player:
            coins, actions = guaranteed_play_resources(
                state, player, pending["card"], followups=pending["followups"],
                harbor_pending=pending.get("harbor_pending", 0),
                coins_before=pending.get("coins_before"), inner_coins=pending_coins,
                harbor_after_followups=pending.get("harbor_after_followups", False),
            )
            pending_coins += coins
            pending_actions += actions
        pending = pending.get("outer")
    money = player.coins + player.coin_tokens + pending_coins + sum(treasure_income(c) for c in hand)
    # Reuse engine affordability for live restrictions and effective costs.
    # The baseline reserves coin-only Supply buys, not Events/Projects or
    # future Potion income; the $3 building floor remains a policy choice.
    affordable = state._get_affordable_cards(player, available_coins=money)
    supply_buys = [
        card for card in affordable
        if not getattr(card, "is_event", False) and not getattr(card, "is_project", False)
        and card.name not in state.non_supply_pile_names
        and card.cost.debt == 0 and card.cost.potions == 0
    ]
    costs = [3, *(state.get_card_cost(player, card) for card in supply_buys)]
    floor = max((cost for cost in costs if cost <= money), default=money)
    # There may be no next turn when buying the final Province/Colony.
    if buys_available and any(
        card.name in {"Province", "Colony"} and state.supply.get(card.name) == 1
        for card in supply_buys
    ):
        return []

    def next_value(card):
        return (card.stats.cards * 2 + card.stats.coins, card.cost.coins, card.name)

    # Retain hybrids while their other ordinary play phase is still available.
    # Use the live Treasure type so Capitalism is covered as well as Crown.
    action_only = [
        c for c in hand if c.is_action
        and not (treasures_playable and state.is_treasure(c))
        and not (night_playable and c.is_night)
    ]
    def available_actions(card):
        printed = 0 if player.ignore_action_bonuses else card.stats.actions
        return printed + guaranteed_play_resources(state, player, card)[1]

    terminals = sorted(
        (c for c in action_only if available_actions(c) == 0),
        key=next_value, reverse=True,
    )
    # A Village or cantrip must remain usable this turn; account for its support.
    action_budget = (
        player.actions + player.villagers + pending_actions
        if actions_playable else 0
    )
    if action_budget > 0:
        action_budget += sum(max(0, available_actions(c) - 1) for c in hand if state.is_action(c))
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
        income = treasure_income(card)
        if card.stats.coins > 0 and money - income >= floor:
            selected.append(card)
            money -= income
    return selected


def barge_should_resolve_now(state, player) -> bool:
    """Compare printed draw utility now and next turn without peeking at order.

    A remaining Action (or Villager) makes draw usable immediately. Otherwise
    discount stranded terminal Actions. Future resources are discounted by 20%;
    special engines should override this deliberately bounded estimate.
    """
    from dominion.ways.chameleon import _chameleon_is_active

    own_turn = player is state.turn_player
    before_buy = own_turn and state.phase in {"start", "action", "treasure"}
    money = player.coins + player.coin_tokens + sum(
        c.stats.coins for c in player.hand if state.is_treasure(c)
    )
    if own_turn and state.phase in {"start", "action", "treasure", "buy"}:
        affordable = state._get_affordable_cards(player, available_coins=money)
        if player.buys > 0 and any(
            c.name in {"Province", "Colony"} and state.supply.get(c.name) == 1
            for c in affordable
        ):
            return True  # Do not save resources beyond a likely game end.
    if _chameleon_is_active(player) and before_buy:
        return True  # The immediate payload is +$3, not draw.
    if not before_buy:
        return False
    pool = player.deck + player.discard
    if not pool:
        return False  # Cleanup will provide next turn's draw pool.
    if state.phase in {"start", "action"} and player.actions + player.villagers > 0:
        return True
    # With no Actions left, money still works this turn; terminal draw does not.
    immediate = sum(c.stats.coins for c in pool if state.is_treasure(c))
    future = immediate + sum(
        c.stats.cards * 2 + c.stats.coins for c in pool if c.is_action and not state.is_treasure(c)
    )
    # An extra Buy is useful with money for two modest purchases.
    buy_value = len(pool) / 3 if money >= 6 and player.buys <= 1 else 0
    return immediate + buy_value >= .8 * future


def sleigh_reaction(state, player, gained_card):
    """Spend Sleigh on useful acceleration, accounting for phases and cost.

    Keep a playable Sleigh's two Horses when a weak gain would replace it.
    After Action/Treasure play has passed, a useful gain belongs on the deck.
    Decline junk, dead points, and gains already at the desired destination.
    """
    destination = getattr(state, "_gain_destinations", {}).get(gained_card)
    if destination is None or gained_card not in destination:
        return None  # Another gain effect already moved it.
    if gained_card.name in {"Curse", "Copper"} or gained_card.is_ruins:
        return None
    if not (gained_card.is_action or state.is_treasure(gained_card) or gained_card.is_night):
        return None
    own_turn = player is state.turn_player
    action_phase = own_turn and state.phase in {"start", "action"}
    treasure_phase = own_turn and state.phase in {"start", "action", "treasure"}
    night_phase = own_turn and state.phase in {"start", "action", "treasure", "buy", "night"}
    usable = (
        gained_card.is_action and action_phase and player.actions + player.villagers > 0
        or state.is_treasure(gained_card) and treasure_phase
        or gained_card.is_night and night_phase
    )
    if usable:
        if destination is player.hand:
            return None
        # Consuming the last playable Sleigh for Silver loses two Horses.
        if action_phase and player.actions + player.villagers == 1 and gained_card.name == "Silver":
            return None
        return "hand"
    if destination is player.deck:
        return None
    return "deck"


def torturer_discards(state, player, choices, count):
    """Preserve next-hand economy and playable Actions; discard dead cards first.

    The responder's Action phase has usually not begun: use a fresh one-Action
    budget plus printed village support, rather than the attacker's resources.
    """
    budget = 1 + player.villagers + sum(max(0, c.stats.actions - 1) for c in choices if c.is_action)
    terminals = sorted((c for c in choices if c.is_action and c.stats.actions == 0),
                       key=lambda c: (c.stats.cards * 2 + c.stats.coins, c.cost.coins, c.name), reverse=True)
    stranded = terminals[budget:]

    def value(card):
        if card.name == "Curse" or (card.is_victory and not card.is_action and not state.is_treasure(card)):
            return -1
        if card in stranded:
            return 0
        if state.is_treasure(card):
            return card.stats.coins * 2
        if card.is_action:
            return 2 + card.stats.cards * 2 + card.stats.coins * 2 + max(0, card.stats.actions - 1) * 3
        return 3 if card.is_night else 1

    return sorted(choices, key=lambda c: (value(c), discard_priority(c)))[:max(0, count)]


def torturer_should_discard_preserving_buy(state, player):
    """Take a free empty-pile Curse; otherwise compare the next hand's loss.

    Dead points and stranded terminals are cheap. Copper is expendable only
    when discarding it preserves the hand's attainable Supply buy breakpoint.
    This models printed resources, not future draws, trashers or all reactions.
    """
    if state.supply.get("Curse", 0) <= 0:
        return False
    picks = torturer_discards(state, player, list(player.hand), min(2, len(player.hand)))
    if not picks:
        return True
    money = sum(c.stats.coins for c in player.hand if state.is_treasure(c))
    remaining = money - sum(c.stats.coins for c in picks if state.is_treasure(c))
    from dominion.cards.registry import get_card

    candidates = [get_card(name) for key, n in list(state.supply.items())
                  if n > 0 and key not in state.non_supply_pile_names
                  and (name := state.top_supply_card(key)) is not None]
    costs = [3, *(state.get_card_cost(player, card) for card in candidates
                 if card.cost.potions == 0 and card.cost.debt == 0)]
    floor = max((cost for cost in costs if cost <= money), default=money)
    # The ranked prefix is cheap only if it consists entirely of dead cards,
    # stranded terminals, or Copper that does not lower this hand's purchase.
    budget = 1 + player.villagers + sum(max(0, c.stats.actions - 1) for c in player.hand if c.is_action)
    terminals = sorted((c for c in player.hand if c.is_action and c.stats.actions == 0),
                       key=lambda c: (c.stats.cards * 2 + c.stats.coins, c.cost.coins, c.name), reverse=True)
    return all(
        c.name == "Curse" or (c.is_victory and not c.is_action and not state.is_treasure(c))
        or c in terminals[budget:] or (c.name == "Copper" and remaining >= floor)
        for c in picks
    )



def torturer_should_discard(state, player):
    """Avoid deck pollution by giving up dead cards, Copper or excess terminals.

    Seeded evaluation found that protecting a single hand's buy breakpoint
    accumulated too many Curses in money decks. Keep the historical Copper
    tolerance; strategies may opt into torturer_should_discard_preserving_buy.
    """
    if state.supply.get("Curse", 0) <= 0:
        return False
    picks = torturer_discards(state, player, list(player.hand), min(2, len(player.hand)))
    budget = 1 + player.villagers + sum(max(0, c.stats.actions - 1) for c in player.hand if c.is_action)
    terminals = sorted((c for c in player.hand if c.is_action and c.stats.actions == 0),
                       key=lambda c: (c.stats.cards * 2 + c.stats.coins, c.cost.coins, c.name), reverse=True)
    return all(
        c.name in {"Curse", "Copper"}
        or (c.is_victory and not c.is_action and not state.is_treasure(c))
        or c in terminals[budget:]
        for c in picks
    )

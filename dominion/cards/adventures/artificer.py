"""Artificer ($5): +1 Card +1 Action +$1. Discard any number of cards. You
may gain a card onto your deck costing exactly $1 per card discarded."""

from ..base_card import Card, CardCost, CardStats, CardType


class Artificer(Card):
    def __init__(self):
        super().__init__(
            name="Artificer",
            cost=CardCost(coins=5),
            stats=CardStats(cards=1, actions=1, coins=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        # Strategies can select the discard independently of a desired gain.
        # None preserves the legacy plan-a-gain policy; [] explicitly discards 0.
        selected = player.ai.choose_artificer_discards(
            game_state, player, list(player.hand)
        )
        planned = None
        if selected is None:
            candidates = _gain_candidates(game_state, player, len(player.hand))
            planned = player.ai.choose_artificer_gain(game_state, player, candidates)
            if planned not in candidates:
                planned = None
            target_cost = game_state.get_card_cost(player, planned) if planned else 0
            selected = []
            remaining = list(player.hand)
            # Retain the existing junk-first baseline for legacy gain hooks.
            for junk in (True, False):
                pool = [c for c in remaining if is_artificer_junk(c) == junk]
                needed = target_cost - len(selected)
                if needed <= 0 or not pool:
                    continue
                order = player.ai.choose_cards_to_discard(
                    game_state, player, list(pool), needed, reason="artificer"
                )
                for card in order or []:
                    if card in pool and card in remaining and len(selected) < target_cost:
                        selected.append(card)
                        remaining.remove(card)
                for card in sorted(pool, key=lambda c: (c.cost.coins, c.name)):
                    if card in remaining and len(selected) < target_cost:
                        selected.append(card)
                        remaining.remove(card)

        # Validate the whole selection against the original physical hand.
        original = list(player.hand)
        discards = []
        for card in selected:
            if card in original:
                discards.append(card)
                original.remove(card)
        discarded = 0
        for card in discards:
            if card in player.hand:
                player.hand.remove(card)
                discarded += 1
                game_state.discard_card(player, card)

        # Discard reactions may change costs or consume an exposed pile member.
        candidates = [c for c in _gain_candidates(game_state, player, discarded)
                      if game_state.get_card_cost(player, c) == discarded]
        chosen = player.ai.choose_artificer_gain_after_discard(
            game_state, player, list(candidates), planned
        )
        from ..gain_decisions import resolve_gain

        chosen = resolve_gain(chosen, candidates)
        if chosen is not None:
            game_state.gain_from_supply(player, chosen.name, destination="deck")


def _gain_candidates(game_state, player, maximum):
    choices = []
    seen = set()
    for pile in game_state.supply:
        card = _exposed_supply_card(game_state, pile)
        if card is not None and card.name not in seen and (
            card.cost.potions == 0 and card.cost.debt == 0
            and game_state.get_card_cost(player, card) <= maximum
        ):
            choices.append(card)
            seen.add(card.name)
    return choices



def is_artificer_junk(card) -> bool:
    """Cards the default Artificer policy is willing to discard.

    Curses, Coppers and non-Action Victory cards. ``BaseAI.choose_artificer_gain``
    budgets the gain cost from this set and ``Artificer.play_effect`` spends it
    before any other card, so the two must agree.
    """
    return (
        card.name == "Curse"
        or card.name == "Copper"
        or (card.is_victory and not card.is_action)
    )


def _exposed_supply_card(game_state, pile_name):
    """The card a gainer would take from ``pile_name`` (top of ordered piles).

    Split piles (Catapult/Rocks, Castles, the Allies rotating piles) keep one
    ``supply`` count per member, so iterating ``game_state.supply`` visits
    buried members too. Only the physically exposed card is offered: this is
    the card ``take_top_supply_card(supply_pile_key(name))`` will remove.
    """

    if game_state.supply.get(pile_name, 0) <= 0:
        return None
    if pile_name in getattr(game_state, "non_supply_pile_names", ()):
        return None
    if pile_name in game_state.pile_order:
        return game_state.top_of_pile(pile_name)
    from ..registry import get_card

    try:
        card = get_card(pile_name)
    except ValueError:
        return None
    if game_state.top_supply_card(pile_name) != pile_name:
        return None  # buried under another member of its split pile
    if not card.may_be_gained(game_state):
        return None
    return card

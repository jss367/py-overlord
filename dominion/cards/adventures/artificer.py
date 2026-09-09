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

        max_discard = len(player.hand)
        candidates = []
        for pile_name in list(game_state.supply):
            card = _exposed_supply_card(game_state, pile_name)
            if card is None:
                continue
            if card.cost.potions > 0 or card.cost.debt > 0:
                continue
            if game_state.get_card_cost(player, card) <= max_discard:
                candidates.append(card)

        if not candidates:
            return

        chosen = player.ai.choose_artificer_gain(game_state, player, candidates)
        if chosen is None or chosen not in candidates:
            return

        target_cost = game_state.get_card_cost(player, chosen)
        if target_cost > max_discard:
            return

        cards_to_discard: list = []
        if target_cost > 0:
            # The default gain hook budgets the cost by the junk in hand, so
            # spend that junk first. The generic discard ordering ranks by
            # printed cost and would otherwise throw a $3 Scheme before a
            # Duchy. Useful cards are only offered when a strategy's own
            # ``choose_artificer_gain`` chose a cost the junk cannot cover.
            remaining_hand = list(player.hand)
            junk = [c for c in remaining_hand if is_artificer_junk(c)]
            useful = [c for c in remaining_hand if not is_artificer_junk(c)]
            for pool in (junk, useful):
                needed = target_cost - len(cards_to_discard)
                if needed <= 0 or not pool:
                    continue
                discard_order = player.ai.choose_cards_to_discard(
                    game_state, player, pool, needed, reason="artificer",
                )
                for card in discard_order:
                    if card in remaining_hand and len(cards_to_discard) < target_cost:
                        cards_to_discard.append(card)
                        remaining_hand.remove(card)

            while len(cards_to_discard) < target_cost and remaining_hand:
                fallback = min(remaining_hand, key=lambda c: (c.cost.coins, c.name))
                cards_to_discard.append(fallback)
                remaining_hand.remove(fallback)

            if len(cards_to_discard) < target_cost:
                return

        for card in cards_to_discard:
            if card in player.hand:
                player.hand.remove(card)
                game_state.discard_card(player, card)

        gained = game_state.take_top_supply_card(game_state.supply_pile_key(chosen.name))
        if gained is None:
            return
        game_state.gain_card(player, gained, to_deck=True)


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

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
            discard_order = player.ai.choose_cards_to_discard(
                game_state, player, list(player.hand), target_cost,
                reason="artificer",
            )
            remaining_hand = list(player.hand)
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


def _exposed_supply_card(game_state, pile_name):
    """The card a gainer would take from ``pile_name`` (top of ordered piles)."""

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
    if not card.may_be_gained(game_state):
        return None
    return card

"""Implementation of the Artificer discard-for-gain card."""

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
        if not player.hand:
            return

        from ..registry import get_card

        max_discard = len(player.hand)
        affordable = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            card = get_card(name)
            if card.cost.potions > 0:
                continue
            if card.cost.coins <= max_discard:
                affordable.append(card)

        if not affordable:
            return

        chosen_gain = player.ai.choose_buy(game_state, affordable + [None])
        if chosen_gain is None:
            return

        target_cost = chosen_gain.cost.coins
        if target_cost > max_discard:
            return

        cards_to_discard: list = []
        if target_cost > 0:
            discard_order = player.ai.choose_cards_to_discard(
                game_state, player, list(player.hand), target_cost
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

        game_state.supply[chosen_gain.name] -= 1
        gained = game_state.gain_card(player, chosen_gain)

        if gained in player.discard:
            player.discard.remove(gained)
            player.hand.append(gained)
        elif gained in player.deck:
            player.deck.remove(gained)
            player.hand.append(gained)
        elif gained not in player.hand:
            player.hand.append(gained)

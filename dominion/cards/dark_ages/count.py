"""Simplified implementation of the Count card."""

from ..base_card import Card, CardCost, CardStats, CardType


class Count(Card):
    def __init__(self):
        super().__init__(
            name="Count",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        self._resolve_first_choice(game_state, player)
        self._resolve_second_choice(game_state, player)

    def _resolve_first_choice(self, game_state, player):
        hand = list(player.hand)
        if len(hand) >= 2:
            to_discard = player.ai.choose_cards_to_discard(game_state, player, hand, 2)
            while len(to_discard) < 2 and hand:
                candidate = min(hand, key=lambda c: (c.cost.coins, c.name))
                if candidate not in to_discard:
                    to_discard.append(candidate)
                hand.remove(candidate)
            for card in to_discard[:2]:
                if card in player.hand:
                    player.hand.remove(card)
                    game_state.discard_card(player, card)
            return

        if hand:
            keep = max(hand, key=lambda c: (c.cost.coins, c.stats.cards, c.name))
            if keep in player.hand:
                player.hand.remove(keep)
                player.deck.append(keep)
            return

        if game_state.supply.get("Copper", 0) > 0:
            from ..registry import get_card

            copper = get_card("Copper")
            game_state.supply["Copper"] -= 1
            game_state.gain_card(player, copper)

    def _resolve_second_choice(self, game_state, player):
        hand = list(player.hand)
        junk_cards = [card for card in hand if card.name in {"Curse", "Estate", "Copper"}]

        if hand and len(junk_cards) >= len(hand) - 1:
            for card in list(player.hand):
                player.hand.remove(card)
                game_state.trash_card(player, card)
            return

        if game_state.supply.get("Duchy", 0) > 0 and game_state.turn_number >= 10:
            from ..registry import get_card

            duchy = get_card("Duchy")
            game_state.supply["Duchy"] -= 1
            game_state.gain_card(player, duchy)
        else:
            player.coins += 3

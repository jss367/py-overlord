from ..base_card import Card, CardCost, CardStats, CardType


class Souk(Card):
    def __init__(self):
        super().__init__(
            name="Souk",
            cost=CardCost(coins=5),
            stats=CardStats(buys=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        coins = max(0, 7 - len(player.hand))
        player.coins += coins

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)

        to_trash = self._select_cards_to_trash(player.hand)
        for card in to_trash:
            if card in player.hand:
                player.hand.remove(card)
                game_state.trash_card(player, card)

    @staticmethod
    def _select_cards_to_trash(hand):
        priority = []
        for card in hand:
            if card.name == "Curse":
                priority.append((0, card))
            elif card.is_victory and not card.is_action:
                priority.append((1, card))
            elif card.name == "Copper":
                priority.append((2, card))
        priority.sort(key=lambda item: (item[0], item[1].cost.coins, item[1].name))
        return [card for _, card in priority[:2]]

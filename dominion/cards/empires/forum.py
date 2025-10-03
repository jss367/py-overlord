from ..base_card import Card, CardCost, CardStats, CardType


class Forum(Card):
    def __init__(self):
        super().__init__(
            name="Forum",
            cost=CardCost(coins=5),
            stats=CardStats(actions=1, cards=3),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        hand_copy = list(player.hand)
        preferred_discards = player.ai.choose_cards_to_discard(
            game_state, player, hand_copy, 2, reason="forum"
        )

        discarded = 0
        for card in preferred_discards:
            if card in player.hand:
                player.hand.remove(card)
                game_state.discard_card(player, card)
                discarded += 1
                if discarded == 2 or not player.hand:
                    return

        while discarded < 2 and player.hand:
            fallback = min(player.hand, key=lambda c: (c.cost.coins, c.name))
            player.hand.remove(fallback)
            game_state.discard_card(player, fallback)
            discarded += 1

        for _ in range(2):
            if player.hand:
                game_state.discard_card(player, player.hand.pop())

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)
        player.buys += 1


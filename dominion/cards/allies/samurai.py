from ..base_card import Card, CardCost, CardStats, CardType


class Samurai(Card):
    """Action - Attack that stays in play.

    When you play this, each other player with 5 or more cards in hand
    discards down to 3. While this is in play, +1 Coin at the start of
    each of your turns.
    """

    def __init__(self):
        super().__init__(
            name="Samurai",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.ATTACK, CardType.DURATION],
        )
        self.duration_persistent = True

    def play_effect(self, game_state):
        player = game_state.current_player

        def attack_target(target):
            if len(target.hand) < 5:
                return

            discard_needed = len(target.hand) - 3
            selected = target.ai.choose_cards_to_discard(
                game_state, target, list(target.hand), discard_needed, reason="samurai"
            )

            for card in selected[:discard_needed]:
                if card in target.hand:
                    target.hand.remove(card)
                    game_state.discard_card(target, card)

            while len(target.hand) > 3:
                card = target.hand[-1]
                target.hand.remove(card)
                game_state.discard_card(target, card)

        for other in game_state.players:
            if other is player:
                continue
            game_state.attack_player(other, attack_target)

        # Stays in play to provide +1 Coin at the start of each future turn
        player.duration.append(self)
        self.duration_persistent = True

    def on_duration(self, game_state):
        player = game_state.current_player
        player.coins += 1
        # Samurai never leaves play on its own
        self.duration_persistent = True

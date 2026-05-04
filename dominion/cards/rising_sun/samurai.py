from ..base_card import Card, CardCost, CardStats, CardType


class Samurai(Card):
    """Action-Duration-Attack ($6).

    When you play this, each other player discards down to 3 cards in hand.
    The Samurai stays in play, and produces +$1 at the start of each of your
    turns for the rest of the game.
    """

    def __init__(self):
        super().__init__(
            name="Samurai",
            cost=CardCost(coins=6),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.ATTACK, CardType.DURATION],
        )
        self.duration_persistent = True

    def play_effect(self, game_state):
        player = game_state.current_player

        def attack_target(target):
            if len(target.hand) <= 3:
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

        player.duration.append(self)
        self.duration_persistent = True

    def on_duration(self, game_state):
        player = game_state.current_player
        player.coins += 1
        self.duration_persistent = True

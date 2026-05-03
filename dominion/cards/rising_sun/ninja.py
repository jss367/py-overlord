from ..base_card import Card, CardCost, CardStats, CardType


class Ninja(Card):
    """Action-Shadow-Attack ($4): +1 Card.
    Each other player discards down to 3 cards in hand.
    """

    def __init__(self):
        super().__init__(
            name="Ninja",
            cost=CardCost(coins=4),
            stats=CardStats(cards=1),
            types=[CardType.ACTION, CardType.ATTACK, CardType.SHADOW],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        def attack_target(target):
            if len(target.hand) <= 3:
                return
            discard_needed = len(target.hand) - 3
            chosen = target.ai.choose_cards_to_discard(
                game_state, target, list(target.hand), discard_needed, reason="ninja"
            )
            for card in chosen[:discard_needed]:
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

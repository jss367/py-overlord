from ..base_card import Card, CardCost, CardStats, CardType


class Rabble(Card):
    def __init__(self):
        super().__init__(
            name="Rabble",
            cost=CardCost(coins=5),
            stats=CardStats(cards=3),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        def attack_target(target):
            revealed = []
            for _ in range(3):
                if not target.deck and target.discard:
                    target.shuffle_discard_into_deck()
                if not target.deck:
                    break
                revealed.append(target.deck.pop())

            to_discard = [c for c in list(revealed) if c.is_action or c.is_treasure]
            for card in to_discard:
                if card in revealed:
                    revealed.remove(card)
                    game_state.discard_card(target, card)

            if revealed:
                ordered = target.ai.order_cards_for_topdeck(
                    game_state, target, list(revealed)
                )
                if set(ordered) != set(revealed) or len(ordered) != len(revealed):
                    ordered = revealed
                for card in reversed(ordered):
                    if card in revealed:
                        revealed.remove(card)
                        target.deck.append(card)

        for other in game_state.players:
            if other is player:
                continue
            game_state.attack_player(other, attack_target)

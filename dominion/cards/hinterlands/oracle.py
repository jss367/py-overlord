from ..base_card import Card, CardCost, CardStats, CardType


class Oracle(Card):
    def __init__(self):
        super().__init__(
            name="Oracle",
            cost=CardCost(coins=3),
            stats=CardStats(cards=2),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        def resolve(target, is_self: bool):
            revealed = []
            for _ in range(2):
                if not target.deck and target.discard:
                    target.shuffle_discard_into_deck()
                if not target.deck:
                    break
                revealed.append(target.deck.pop())

            if not revealed:
                return

            total = sum(self._card_value(card) for card in revealed)
            if is_self:
                if total < 0:
                    for card in revealed:
                        game_state.discard_card(target, card)
                else:
                    while revealed:
                        target.deck.append(revealed.pop())
            else:
                if total > 1:
                    for card in revealed:
                        game_state.discard_card(target, card)
                else:
                    while revealed:
                        target.deck.append(revealed.pop())

        resolve(player, True)
        for other in game_state.players:
            if other is player:
                continue
            game_state.attack_player(other, lambda t, _resolve=resolve: _resolve(t, False))

    @staticmethod
    def _card_value(card) -> int:
        if card.name == "Curse":
            return -3
        if card.is_victory and not card.is_action:
            return -2
        if card.is_treasure:
            return 2 + card.cost.coins
        if card.is_action:
            return 2
        return 0

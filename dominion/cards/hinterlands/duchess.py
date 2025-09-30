from ..base_card import Card, CardCost, CardStats, CardType


class Duchess(Card):
    def __init__(self):
        super().__init__(
            name="Duchess",
            cost=CardCost(coins=2),
            stats=CardStats(coins=2),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        self._review_top_card(game_state, player, is_self=True)
        for other in game_state.players:
            if other is player:
                continue
            self._review_top_card(game_state, other, is_self=False)

    def _review_top_card(self, game_state, target, *, is_self: bool) -> None:
        if not target.deck and target.discard:
            target.shuffle_discard_into_deck()
        if not target.deck:
            return

        card = target.deck.pop()
        should_discard = self._should_discard(card, is_self)
        if should_discard:
            game_state.discard_card(target, card)
        else:
            target.deck.append(card)

    @staticmethod
    def _should_discard(card, is_self: bool) -> bool:
        if card.name == "Curse":
            return True
        if card.is_victory and not card.is_action:
            return True
        if is_self and card.name == "Copper":
            return True
        return False

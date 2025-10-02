"""Implementation of the Sentry top-decker."""

from ..base_card import Card, CardCost, CardStats, CardType


class Sentry(Card):
    def __init__(self):
        super().__init__(
            name="Sentry",
            cost=CardCost(coins=5),
            stats=CardStats(actions=1, cards=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        revealed = []
        for _ in range(2):
            if not player.deck and player.discard:
                player.shuffle_discard_into_deck()
            if not player.deck:
                break
            revealed.append(player.deck.pop())

        if not revealed:
            return

        kept: list = []
        for card in revealed:
            if self._should_trash(card):
                game_state.trash_card(player, card)
            elif self._should_discard(card):
                game_state.discard_card(player, card)
            else:
                kept.append(card)

        if kept:
            ordered = player.ai.order_cards_for_topdeck(game_state, player, list(kept))
            if set(ordered) != set(kept) or len(ordered) != len(kept):
                ordered = kept
            for card in reversed(ordered):
                if card in kept:
                    kept.remove(card)
                    player.deck.append(card)

    @staticmethod
    def _should_trash(card):
        if card.name == "Curse":
            return True
        if card.is_victory and not card.is_action and card.cost.coins <= 2:
            return True
        if card.name == "Copper":
            return True
        return False

    @staticmethod
    def _should_discard(card):
        if card.is_victory and not card.is_action:
            return True
        return False

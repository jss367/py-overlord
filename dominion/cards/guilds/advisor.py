from ..base_card import Card, CardCost, CardStats, CardType


class Advisor(Card):
    """Reveal three cards; an opponent discards one, the rest to hand."""

    def __init__(self):
        super().__init__(
            name="Advisor",
            cost=CardCost(coins=4),
            stats=CardStats(actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        revealed: list = []
        for _ in range(3):
            if not player.deck and player.discard:
                player.shuffle_discard_into_deck()
            if not player.deck:
                break
            revealed.append(player.deck.pop())

        if not revealed:
            return

        discard_choice = max(revealed, key=self._card_value)
        game_state.discard_card(player, discard_choice)

        for card in revealed:
            if card is discard_choice:
                continue
            player.hand.append(card)

    @staticmethod
    def _card_value(card) -> int:
        if card.name == "Curse":
            return -5
        value = card.cost.coins
        if card.is_treasure:
            value += 5
        if card.is_action:
            value += 4
        if card.is_victory and not card.is_action:
            value -= 1
        return value

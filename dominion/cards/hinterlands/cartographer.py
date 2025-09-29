from ..base_card import Card, CardCost, CardStats, CardType


class Cartographer(Card):
    def __init__(self):
        super().__init__(
            name="Cartographer",
            cost=CardCost(coins=5),
            stats=CardStats(actions=1, cards=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        revealed = []
        for _ in range(4):
            if not player.deck and player.discard:
                player.shuffle_discard_into_deck()
            if not player.deck:
                break
            revealed.append(player.deck.pop())

        kept: list[tuple[int, Card]] = []
        for card in revealed:
            score = self._card_score(card)
            if score < 0:
                game_state.discard_card(player, card)
            else:
                kept.append((score, card))

        kept.sort()
        for _, card in kept:
            player.deck.append(card)

    @staticmethod
    def _card_score(card: Card) -> int:
        if card.name == "Curse":
            return -3
        if card.is_victory and not card.is_action:
            return -2
        if card.is_treasure:
            return 2 + card.cost.coins
        if card.is_action:
            return 1
        return 0

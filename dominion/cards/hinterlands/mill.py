from ..base_card import Card, CardCost, CardStats, CardType


class Mill(Card):
    """Mill provides small cycling and a discard for coins option."""

    def __init__(self):
        super().__init__(
            name="Mill",
            cost=CardCost(coins=4),
            stats=CardStats(actions=1, cards=1, vp=1),
            types=[CardType.ACTION, CardType.VICTORY],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        if len(player.hand) < 2:
            return

        # Simple heuristic: discard junky cards first to trigger the +2 coins.
        priority = []
        for card in player.hand:
            score = 2
            if card.name == "Curse":
                score = 0
            elif card.is_victory and card.name != "Mill":
                score = 1
            elif card.name == "Copper":
                score = 3
            elif card.is_treasure:
                score = 4
            priority.append((score, card))

        priority.sort(key=lambda item: (item[0], item[1].name))
        discards = [card for _, card in priority[:2]]

        for card in discards:
            player.hand.remove(card)
            game_state.discard_card(player, card)

        if len(discards) == 2:
            player.coins += 2

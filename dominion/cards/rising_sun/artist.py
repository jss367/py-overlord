from ..base_card import Card, CardCost, CardStats, CardType


class Artist(Card):
    """Action ($8 Debt): +1 Action.
    +1 Card per card you have exactly one copy of in play.

    Counts cards still in play from previous turns (e.g. Samurai). The
    cost is pure Debt — buying it takes 8 Debt.
    """

    def __init__(self):
        super().__init__(
            name="Artist",
            cost=CardCost(coins=0, debt=8),
            stats=CardStats(actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        # Count cards in play (across in_play + duration). For each card
        # name that appears exactly once, give +1 Card.
        from collections import Counter

        names = [c.name for c in player.in_play + player.duration]
        counts = Counter(names)
        unique_singletons = sum(1 for n, c in counts.items() if c == 1)
        if unique_singletons > 0:
            game_state.draw_cards(player, unique_singletons)

"""Fortune Hunter from the Plunder expansion."""

from ..base_card import Card, CardCost, CardStats, CardType


class FortuneHunter(Card):
    """$4 Action: +$2. Look at top 3 cards of deck. Play any number of revealed
    Treasures in any order, then put the rest back on top in any order.
    """

    def __init__(self):
        super().__init__(
            name="Fortune Hunter",
            cost=CardCost(coins=4),
            stats=CardStats(coins=2),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        revealed = []
        for _ in range(3):
            if not player.deck and player.discard:
                player.shuffle_discard_into_deck()
            if not player.deck:
                break
            revealed.append(player.deck.pop())

        if not revealed:
            return

        treasures = [c for c in revealed if c.is_treasure]
        non_treasures = [c for c in revealed if not c.is_treasure]

        played: list = []
        remaining = list(treasures)
        while remaining:
            choice = player.ai.choose_treasure(
                game_state, list(remaining) + [None]
            )
            if choice is None or choice not in remaining:
                break
            remaining.remove(choice)
            played.append(choice)

        for card in played:
            player.in_play.append(card)
            card.on_play(game_state)

        leftover = remaining + non_treasures
        for card in reversed(leftover):
            player.deck.append(card)

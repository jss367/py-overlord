"""Seer: Action ($5). +1 Card. +1 Action.

Reveal the top 3 cards of your deck. Put each costing $2-$4 into your
hand. Put the rest back in any order.
"""

from ..base_card import Card, CardCost, CardStats, CardType


class Seer(Card):
    def __init__(self) -> None:
        super().__init__(
            name="Seer",
            cost=CardCost(coins=5),
            stats=CardStats(cards=1, actions=1),
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

        keep = [c for c in revealed if 2 <= c.cost.coins <= 4]
        leftover = [c for c in revealed if c not in keep]

        for card in keep:
            player.hand.append(card)
        # Put leftovers back in any order — top of deck is the end of list.
        # Order them so the cheapest junk is drawn last (insert junk first).
        leftover.sort(key=lambda c: (c.cost.coins, c.name))
        for card in leftover:
            player.deck.append(card)

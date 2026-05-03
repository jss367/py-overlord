"""Mapmaker from the Plunder expansion."""

from ..base_card import Card, CardCost, CardStats, CardType


class Mapmaker(Card):
    """$4 Action: Look at top 4 cards of your deck. Put 2 into your hand,
    discard the rest.
    """

    def __init__(self):
        super().__init__(
            name="Mapmaker",
            cost=CardCost(coins=4),
            stats=CardStats(),
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

        if not revealed:
            return

        keep_count = min(2, len(revealed))

        chosen: list = []
        remaining = list(revealed)
        for _ in range(keep_count):
            if not remaining:
                break
            pick = player.ai.choose_action(game_state, list(remaining) + [None])
            if pick is None or pick not in remaining:
                pick = remaining[0]
            remaining.remove(pick)
            chosen.append(pick)

        for card in chosen:
            player.hand.append(card)

        for card in remaining:
            game_state.discard_card(player, card)

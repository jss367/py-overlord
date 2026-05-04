"""Implementation of Scout (1E)."""

from ..base_card import Card, CardCost, CardStats, CardType


class Scout(Card):
    """+1 Action. Reveal the top 4 cards of your deck. Put the Victory cards
    into your hand. Put the others back on top in any order."""

    def __init__(self):
        super().__init__(
            name="Scout",
            cost=CardCost(coins=4),
            stats=CardStats(actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        revealed: list[Card] = []
        for _ in range(4):
            if not player.deck and player.discard:
                player.shuffle_discard_into_deck()
            if not player.deck:
                break
            revealed.append(player.deck.pop())

        if not revealed:
            return

        to_hand: list[Card] = []
        to_topdeck: list[Card] = []
        for card in revealed:
            if card.is_victory:
                to_hand.append(card)
            else:
                to_topdeck.append(card)

        if to_hand:
            player.hand.extend(to_hand)

        if not to_topdeck:
            return

        ordered = player.ai.order_cards_for_scout(
            game_state, player, list(to_topdeck)
        )
        if (
            ordered is None
            or len(ordered) != len(to_topdeck)
            or {id(c) for c in ordered} != {id(c) for c in to_topdeck}
        ):
            ordered = to_topdeck

        # The first card in ``ordered`` is drawn first (most desirable).
        # In our deck representation, top of deck is end of list, so
        # iterate in reverse to put the best card on top.
        for card in reversed(ordered):
            player.deck.append(card)

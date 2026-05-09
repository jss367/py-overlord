from ..base_card import Card, CardCost, CardStats, CardType


class Carnival(Card):
    """+1 Buy. Reveal the top 4 cards of your deck. Put one of each
    differently named card into your hand and discard the rest."""

    def __init__(self):
        super().__init__(
            name="Carnival",
            cost=CardCost(coins=4),
            stats=CardStats(buys=1),
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

        seen_names: set[str] = set()
        for card in revealed:
            if card.name not in seen_names:
                seen_names.add(card.name)
                player.hand.append(card)
            else:
                # Route the discard through the engine so cards with
                # discard-side triggers (Tunnel, Trail, Friendly trait, ...)
                # fire correctly.
                game_state.discard_card(player, card)

"""Implementation of Tribute (1E)."""

from ..base_card import Card, CardCost, CardStats, CardType


class Tribute(Card):
    """The player to your left reveals then discards the top 2 cards of
    their deck. For each differently named card revealed, if it's an
    Action, +2 Actions; if a Treasure, +$2; if a Victory card, +2 Cards."""

    def __init__(self):
        super().__init__(
            name="Tribute",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        players = list(game_state.players)
        idx = players.index(player)
        left = players[(idx + 1) % len(players)]

        revealed: list[Card] = []
        for _ in range(2):
            if not left.deck and left.discard:
                left.shuffle_discard_into_deck()
            if not left.deck:
                break
            revealed.append(left.deck.pop())

        # Apply effects per differently-named card revealed.
        seen_names: set[str] = set()
        for card in revealed:
            if card.name in seen_names:
                continue
            seen_names.add(card.name)
            if card.is_action:
                player.actions += 2
            if card.is_treasure:
                player.coins += 2
            if card.is_victory:
                game_state.draw_cards(player, 2)

        # Discard whatever was revealed.
        for card in revealed:
            game_state.discard_card(left, card)

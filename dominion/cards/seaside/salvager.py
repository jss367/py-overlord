from ..base_card import Card, CardCost, CardStats, CardType


class Salvager(Card):
    """Action ($4): +1 Buy. Trash a card from your hand. +$ equal to its cost."""

    def __init__(self):
        super().__init__(
            name="Salvager",
            cost=CardCost(coins=4),
            stats=CardStats(buys=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        if not player.hand:
            return

        # Trash is mandatory when the hand has cards. Honor the AI's choice
        # when valid; otherwise fall back to the cheapest junk so we don't
        # silently turn Salvager into a free +1 Buy.
        choice = player.ai.choose_card_to_trash(game_state, list(player.hand))
        if choice is None or choice not in player.hand:
            choice = min(
                player.hand,
                key=lambda c: (c.is_action, c.is_treasure, c.cost.coins, c.name),
            )

        cost = game_state.get_card_cost(player, choice)
        player.hand.remove(choice)
        game_state.trash_card(player, choice)
        player.coins += cost

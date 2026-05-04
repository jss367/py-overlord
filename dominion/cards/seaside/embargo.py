from ..base_card import Card, CardCost, CardStats, CardType


class Embargo(Card):
    """Action ($2): +$2. Trash this. Put an Embargo token on a Supply pile.
    When a player buys a card, they gain a Curse per Embargo token on that pile.
    """

    def __init__(self):
        super().__init__(
            name="Embargo",
            cost=CardCost(coins=2),
            stats=CardStats(coins=2),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        # Trash this Embargo
        if self in player.in_play:
            player.in_play.remove(self)
            game_state.trash_card(player, self)

        # Place an Embargo token on a Supply pile
        choice = player.ai.choose_pile_to_embargo(game_state, player)
        if choice is None:
            return

        if choice not in game_state.supply:
            return

        game_state.embargo_tokens[choice] = game_state.embargo_tokens.get(choice, 0) + 1

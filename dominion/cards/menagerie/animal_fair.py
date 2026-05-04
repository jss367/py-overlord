"""Animal Fair - Action from Menagerie."""

from ..base_card import Card, CardCost, CardStats, CardType


class AnimalFair(Card):
    """+$5. You may trash a card from your hand. Cost reduction: this costs
    $2 less per Action card you have in play.
    """

    def __init__(self):
        super().__init__(
            name="Animal Fair",
            cost=CardCost(coins=7),
            stats=CardStats(coins=5),
            types=[CardType.ACTION],
        )

    def cost_modifier(self, game_state, player) -> int:
        actions_in_play = sum(1 for c in player.in_play if c.is_action)
        return -2 * actions_in_play

    def play_effect(self, game_state):
        player = game_state.current_player
        if not player.hand:
            return
        choice = player.ai.choose_card_to_trash(game_state, player.hand + [None])
        if choice is None or choice not in player.hand:
            return
        player.hand.remove(choice)
        game_state.trash_card(player, choice)

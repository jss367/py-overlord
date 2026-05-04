"""Zombie Apprentice — non-supply Action, $3."""

from ...base_card import Card, CardCost, CardStats, CardType


class ZombieApprentice(Card):
    """+1 Card +1 Action. Trash a card from hand."""

    def __init__(self):
        super().__init__(
            name="Zombie Apprentice",
            cost=CardCost(coins=3),
            stats=CardStats(cards=1, actions=1),
            types=[CardType.ACTION, CardType.ZOMBIE],
        )

    def starting_supply(self, game_state) -> int:
        return 1

    def may_be_bought(self, game_state) -> bool:
        return False

    def play_effect(self, game_state):
        player = game_state.current_player
        if not player.hand:
            return
        choice = player.ai.choose_card_to_trash(game_state, list(player.hand))
        if choice is None or choice not in player.hand:
            return
        player.hand.remove(choice)
        game_state.trash_card(player, choice)

"""Maelstrom from the Plunder expansion."""

from ..base_card import Card, CardCost, CardStats, CardType


class Maelstrom(Card):
    """$4 Action-Attack: Trash 3 cards from your hand. Each other player with
    5 or more cards in hand trashes one of them.
    """

    def __init__(self):
        super().__init__(
            name="Maelstrom",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        for _ in range(3):
            if not player.hand:
                break
            choice = player.ai.choose_card_to_trash(
                game_state, list(player.hand) + [None]
            )
            if choice is None or choice not in player.hand:
                # Mandatory trash; pick the first card if AI declines.
                if player.hand:
                    choice = player.hand[0]
                else:
                    break
            player.hand.remove(choice)
            game_state.trash_card(player, choice)

        def attack_target(target):
            if len(target.hand) < 5:
                return
            choice = target.ai.choose_card_to_trash(
                game_state, list(target.hand) + [None]
            )
            if choice is None or choice not in target.hand:
                choice = target.hand[0]
            target.hand.remove(choice)
            game_state.trash_card(target, choice)

        for other in game_state.players:
            if other is player:
                continue
            game_state.attack_player(other, attack_target)

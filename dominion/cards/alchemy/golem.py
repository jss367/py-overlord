"""Golem - Action from Alchemy."""

from ..base_card import Card, CardCost, CardStats, CardType


class Golem(Card):
    """Action ($4P): Reveal cards from your deck until you reveal 2 Action
    cards other than Golems. Discard the other revealed cards, then play the
    Action cards in either order.
    """

    def __init__(self):
        super().__init__(
            name="Golem",
            cost=CardCost(coins=4, potions=1),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        actions_found: list = []
        non_actions: list = []
        while len(actions_found) < 2:
            if not player.deck and player.discard:
                player.shuffle_discard_into_deck()
            if not player.deck:
                break
            card = player.deck.pop()
            if card.is_action and card.name != "Golem":
                actions_found.append(card)
            else:
                non_actions.append(card)

        if non_actions:
            game_state.discard_cards(player, non_actions)

        if not actions_found:
            return

        if len(actions_found) == 2:
            order = player.ai.choose_golem_play_order(
                game_state, player, list(actions_found)
            )
            if order is None or sorted(c.name for c in order) != sorted(
                c.name for c in actions_found
            ):
                order = actions_found
        else:
            order = actions_found

        for action_card in order:
            player.in_play.append(action_card)
            game_state.play_action_indirectly(
                player, action_card, blocked_return_zone=player.discard
            )

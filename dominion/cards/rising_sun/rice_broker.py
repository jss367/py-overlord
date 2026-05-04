from ..base_card import Card, CardCost, CardStats, CardType


class RiceBroker(Card):
    """Action ($5): +1 Action. Trash a card from your hand.
    If a Treasure, +2 Cards. If an Action, +5 Cards.
    (A card that's both gives both, in that order: +2 then +5.)
    """

    def __init__(self):
        super().__init__(
            name="Rice Broker",
            cost=CardCost(coins=5),
            stats=CardStats(actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        if not player.hand:
            return

        chosen = player.ai.choose_card_to_trash(game_state, list(player.hand))
        if chosen is None or chosen not in player.hand:
            return

        is_treasure = chosen.is_treasure
        is_action = chosen.is_action

        player.hand.remove(chosen)
        game_state.trash_card(player, chosen)

        if is_treasure:
            game_state.draw_cards(player, 2)
        if is_action:
            game_state.draw_cards(player, 5)

from ..base_card import Card, CardCost, CardStats, CardType


class RusticVillage(Card):
    """Action-Omen ($4): +1 Sun, +1 Card, +2 Actions.
    You may discard 2 cards (including the one just drawn) for +1 Card.
    """

    def __init__(self):
        super().__init__(
            name="Rustic Village",
            cost=CardCost(coins=4),
            stats=CardStats(cards=1, actions=2),
            types=[CardType.ACTION, CardType.OMEN],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        if len(player.hand) < 2:
            return
        if not player.ai.should_rustic_village_discard(game_state, player):
            return

        chosen = player.ai.choose_cards_to_discard(
            game_state, player, list(player.hand), 2, reason="rustic_village"
        )
        chosen = chosen[:2]
        if len(chosen) < 2:
            return
        for card in chosen:
            if card in player.hand:
                player.hand.remove(card)
                game_state.discard_card(player, card)
        game_state.draw_cards(player, 1)

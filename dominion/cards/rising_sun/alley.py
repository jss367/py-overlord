from ..base_card import Card, CardCost, CardStats, CardType


class Alley(Card):
    """Action-Shadow ($4): +1 Card, +1 Action, discard a card."""

    def __init__(self):
        super().__init__(
            name="Alley",
            cost=CardCost(coins=4),
            stats=CardStats(cards=1, actions=1),
            types=[CardType.ACTION, CardType.SHADOW],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        if not player.hand:
            return
        chosen = player.ai.choose_cards_to_discard(
            game_state, player, list(player.hand), 1, reason="alley"
        )
        if not chosen:
            return
        card = chosen[0]
        if card in player.hand:
            player.hand.remove(card)
            game_state.discard_card(player, card)

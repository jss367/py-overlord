from ..base_card import Card, CardCost, CardStats, CardType


class Pilgrim(Card):
    """Allies $5 — +4 Cards, then top-deck a card from your hand."""

    def __init__(self):
        super().__init__(
            name="Pilgrim",
            cost=CardCost(coins=5),
            stats=CardStats(cards=4),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        if not player.hand:
            return

        choice = player.ai.choose_card_to_topdeck_from_hand(
            game_state, player, list(player.hand), reason="pilgrim"
        )
        if choice is None or choice not in player.hand:
            return

        player.hand.remove(choice)
        player.deck.append(choice)

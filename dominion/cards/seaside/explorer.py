from ..base_card import Card, CardCost, CardStats, CardType


class Explorer(Card):
    """Action ($5): You may reveal a Province from your hand. If you do, gain a Gold
    to your hand. Otherwise, gain a Silver to your hand.
    """

    def __init__(self):
        super().__init__(
            name="Explorer",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player

        target_name = "Silver"
        if any(card.name == "Province" for card in player.hand):
            # Reveal Province (no need to remove it; it's revealed in place) and gain Gold.
            target_name = "Gold"

        if game_state.supply.get(target_name, 0) <= 0:
            return

        game_state.supply[target_name] -= 1
        gained = game_state.gain_card(player, get_card(target_name))

        # Move into hand.
        if gained in player.discard:
            player.discard.remove(gained)
        elif gained in player.deck:
            player.deck.remove(gained)
        if gained not in player.hand:
            player.hand.append(gained)

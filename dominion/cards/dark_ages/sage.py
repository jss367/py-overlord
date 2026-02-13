from ..base_card import Card, CardCost, CardStats, CardType


class Sage(Card):
    def __init__(self):
        super().__init__(
            name="Sage",
            cost=CardCost(coins=3),
            stats=CardStats(actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        """Reveal cards from deck until you find one costing 3+."""
        player = game_state.current_player
        revealed = []

        while True:
            drawn = player.draw_cards(1)
            if not drawn:
                break
            card = drawn[0]
            # Remove from hand since draw_cards puts it there
            player.hand.remove(card)

            if card.cost.coins >= 3:
                # Found one - put it in hand, discard the rest
                player.hand.append(card)
                break
            else:
                revealed.append(card)

        # Discard all revealed cards that didn't qualify
        for card in revealed:
            game_state.discard_card(player, card)

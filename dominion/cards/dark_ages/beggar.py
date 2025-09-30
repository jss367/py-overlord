from ..base_card import Card, CardCost, CardStats, CardType


class Beggar(Card):
    def __init__(self):
        super().__init__(
            name="Beggar",
            cost=CardCost(coins=2),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        for _ in range(3):
            if game_state.supply.get("Copper", 0) <= 0:
                break

            game_state.supply["Copper"] -= 1
            copper = get_card("Copper")
            gained = game_state.gain_card(player, copper)

            if gained in player.discard:
                player.discard.remove(gained)
            elif gained in player.deck:
                player.deck.remove(gained)

            if gained not in player.hand:
                player.hand.append(gained)

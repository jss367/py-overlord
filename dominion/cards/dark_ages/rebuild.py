from ..base_card import Card, CardCost, CardStats, CardType


class Rebuild(Card):
    def __init__(self):
        super().__init__(
            name="Rebuild",
            cost=CardCost(coins=5),
            stats=CardStats(actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        # Simplified: trash an Estate from deck/discard if possible, gain a Duchy
        for pile in [player.hand, player.deck, player.discard]:
            estate = next((c for c in pile if c.name == "Estate"), None)
            if estate:
                pile.remove(estate)
                game_state.trash_card(player, estate)
                if game_state.supply.get("Duchy", 0) > 0:
                    game_state.supply["Duchy"] -= 1
                    duchy = get_card("Duchy")
                    game_state.gain_card(player, duchy)
                return

from ..base_card import Card, CardCost, CardStats, CardType


class Mountebank(Card):
    def __init__(self):
        super().__init__(
            name="Mountebank",
            cost=CardCost(coins=5),
            stats=CardStats(coins=2),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        for other in game_state.players:
            if other is player:
                continue
            curse = next((c for c in other.hand if c.name == "Curse"), None)
            if curse:
                other.hand.remove(curse)
                other.discard.append(curse)
            else:
                from ..registry import get_card
                if game_state.supply.get("Curse", 0) > 0:
                    game_state.supply["Curse"] -= 1
                    gained = get_card("Curse")
                    other.discard.append(gained)
                    gained.on_gain(game_state, other)
                if game_state.supply.get("Copper", 0) > 0:
                    game_state.supply["Copper"] -= 1
                    copper = get_card("Copper")
                    other.discard.append(copper)
                    copper.on_gain(game_state, other)

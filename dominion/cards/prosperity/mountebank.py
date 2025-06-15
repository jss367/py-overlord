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

        def attack_target(target):
            curse = next((c for c in target.hand if c.name == "Curse"), None)
            if curse:
                target.hand.remove(curse)
                target.discard.append(curse)
            else:
                from ..registry import get_card
                if game_state.supply.get("Curse", 0) > 0:
                    game_state.supply["Curse"] -= 1
                    gained = get_card("Curse")
                    target.discard.append(gained)
                    gained.on_gain(game_state, target)
                if game_state.supply.get("Copper", 0) > 0:
                    game_state.supply["Copper"] -= 1
                    copper = get_card("Copper")
                    target.discard.append(copper)
                    copper.on_gain(game_state, target)

        for other in game_state.players:
            if other is player:
                continue
            game_state.attack_player(other, attack_target)

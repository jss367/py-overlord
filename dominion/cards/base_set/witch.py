
from typing import List
from ..base_card import Card, CardCost, CardStats, CardType


class Witch(Card):
    def __init__(self):
        super().__init__(
            name="Witch",
            cost=CardCost(coins=5),
            stats=CardStats(cards=2),
            types=[CardType.ACTION, CardType.ATTACK]
        )
    
    def play_effect(self, game_state):
        """Each other player gains a Curse."""
        current_player = game_state.current_player
        
        for player in game_state.players:
            if player != current_player:
                # Check if Curse is available in supply
                if game_state.supply.get("Curse", 0) > 0:
                    # Gain a Curse
                    curse = Card.get_card("Curse")
                    player.discard.append(curse)
                    game_state.supply["Curse"] -= 1
                    curse.on_gain(game_state, player)

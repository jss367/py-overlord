from typing import List
from ..base_card import Card, CardCost, CardStats, CardType

class Workshop(Card):
    def __init__(self):
        super().__init__(
            name="Workshop",
            cost=CardCost(coins=3),
            stats=CardStats(),
            types=[CardType.ACTION]
        )
    
    def play_effect(self, game_state):
        """Gain a card costing up to 4 coins."""
        player = game_state.current_player
        
        from ..registry import get_card  # Avoid circular import
        
        # Find cards that can be gained
        possible_gains = [
            name for name, count in game_state.supply.items() 
            if count > 0 and get_card(name).cost.coins <= 4
        ]
        
        # Let AI choose what to gain
        if possible_gains:
            chosen_card = player.ai.choose_buy(game_state, 
                [get_card(name) for name in possible_gains])
            
            if chosen_card:
                # Gain the chosen card
                game_state.supply[chosen_card.name] -= 1
                player.discard.append(chosen_card)
                chosen_card.on_gain(game_state, player)

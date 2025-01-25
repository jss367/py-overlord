from typing import Dict, List, Optional

from .base_ai import AI

from dominion.cards.base_card import Card, CardType
from dominion.game.game_state import GameState
from dominion.cards.registry import get_card
from dominion.game.player_state import PlayerState
from dominion.strategies.strategy import Strategy
class GeneticAI(AI):
    """AI that uses a learnable strategy."""
    
    def __init__(self, strategy: Strategy):
        self.strategy = strategy
        self._name = f"GeneticAI-{id(self)}"

    @property
    def name(self) -> str:
        return self._name

    def choose_action(self, state: GameState, choices: List[Optional[Card]]) -> Optional[Card]:
        """Choose an action card to play."""
        valid_choices = [c for c in choices if c is not None]
        if not valid_choices:
            return None
            
        # Get play values for each card
        values = [(self.get_action_value(c, state), c) for c in valid_choices]
        if not values:
            return None
            
        # Return highest value card
        return max(values)[1]

    def choose_treasure(self, state: GameState, choices: List[Optional[Card]]) -> Optional[Card]:
        """Choose a treasure card to play."""
        valid_choices = [c for c in choices if c is not None and c.is_treasure]
        if not valid_choices:
            return None
            
        # Play treasures in descending order of value
        return max(valid_choices, key=lambda c: c.stats.coins)

    def choose_buy(self, state: GameState, choices: List[Optional[Card]]) -> Optional[Card]:
        """Choose a card to buy."""
        valid_choices = [c for c in choices if c is not None]
        if not valid_choices:
            return None
            
        # Get buy values for each card
        values = [(self.get_buy_value(c), c) for c in valid_choices]
        if not values:
            return None
            
        # Return highest value card
        return max(values)[1]

    def get_action_value(self, card: Card, state: GameState) -> float:
        """Calculate how valuable it is to play this action."""
        base_value = self.strategy.play_priorities.get(card.name, 0.0)
        
        # Adjust based on card effects and strategy weights
        if card.stats.actions > 0:
            base_value += self.strategy.action_weight * card.stats.actions
        if card.stats.cards > 0:
            base_value += self.strategy.engine_weight * card.stats.cards
        if card.stats.coins > 0:
            base_value += self.strategy.treasure_weight * card.stats.coins
            
        return base_value

    def get_buy_value(self, card: Card) -> float:
        """Calculate how valuable it is to buy this card."""
        return self.strategy.gain_priorities.get(card.name, 0.0)

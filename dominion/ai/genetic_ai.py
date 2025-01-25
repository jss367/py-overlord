from typing import Optional, Tuple

from .base_ai import AI
from dominion.cards.base_card import Card
from dominion.game.game_state import GameState
from dominion.strategies.strategy import Strategy

class GeneticAI(AI):
    """AI that uses a learnable strategy."""
    
    def __init__(self, strategy: Strategy):
        self.strategy = strategy
        self._name = f"GeneticAI-{id(self)}"

    @property
    def name(self) -> str:
        return self._name

    def choose_action(self, state: GameState, choices: list[Optional[Card]]) -> Optional[Card]:
        """Choose an action card to play."""
        valid_choices = [c for c in choices if c is not None]
        if not valid_choices:
            return None
            
        # Calculate values and pair with cards
        values: list[Tuple[float, Card]] = []
        for card in valid_choices:
            value = self.get_action_value(card, state)
            values.append((value, card))
            
        if not values:
            return None
            
        # Sort by value and return highest value card
        values.sort(key=lambda x: x[0], reverse=True)
        return values[0][1]

    def choose_treasure(self, state: GameState, choices: list[Optional[Card]]) -> Optional[Card]:
        """Choose a treasure card to play."""
        valid_choices = [c for c in choices if c is not None and c.is_treasure]
        if not valid_choices:
            return None
            
        # Sort by coin value and return highest
        treasures = [(c.stats.coins, c) for c in valid_choices]
        treasures.sort(key=lambda x: x[0], reverse=True)
        return treasures[0][1]

    def choose_buy(self, state: GameState, choices: list[Optional[Card]]) -> Optional[Card]:
        """Choose a card to buy."""
        valid_choices = [c for c in choices if c is not None]
        if not valid_choices:
            return None
            
        # Calculate values and pair with cards
        values: list[Tuple[float, Card]] = []
        for card in valid_choices:
            value = self.get_buy_value(card)
            values.append((value, card))
            
        if not values:
            return None
            
        # Sort by value and return highest value card
        values.sort(key=lambda x: x[0], reverse=True)
        return values[0][1]

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

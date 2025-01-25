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
            
            # Prioritize cards that give more actions when we need them
            remaining_actions = state.current_player.actions
            if remaining_actions <= 1 and card.stats.actions > 0:
                value += 1.0
                
            # Prioritize card drawing
            if card.stats.cards > 0:
                value += 0.5 * card.stats.cards
                
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
        base_value = self.strategy.gain_priorities.get(card.name, 0.0)
        
        # Adjust value based on game state and card type
        value = base_value
        
        # Always maintain some interest in basic treasures
        if card.name == "Gold":
            value += 0.5
        elif card.name == "Silver":
            value += 0.3
        elif card.name == "Copper":
            value += 0.1
            
        # Adjust for card costs - prefer cheaper cards early
        value -= (card.cost.coins * 0.1)
        
        # Boost value of cards that help prevent getting stuck
        if card.stats.cards > 0:  # Card drawing
            value += 0.2 * card.stats.cards
        if card.stats.actions > 0:  # Village effects
            value += 0.3 * card.stats.actions
            
        return value

from typing import Optional, Tuple, List
from .base_ai import AI
from dominion.cards.base_card import Card
from dominion.game.game_state import GameState
from dominion.strategies.strategy import Strategy

class GeneticAI(AI):
    """AI that uses a learnable strategy with improved heuristics."""
    
    def __init__(self, strategy: Strategy):
        self.strategy = strategy
        self._name = f"GeneticAI-{id(self)}"

    @property
    def name(self) -> str:
        return self._name

    def choose_action(self, state: GameState, choices: list[Optional[Card]]) -> Optional[Card]:
        """Choose an action card to play using improved action sequencing."""
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
        """Choose a treasure card to play with improved coin optimization."""
        valid_choices = [c for c in choices if c is not None and c.is_treasure]
        if not valid_choices:
            return None

        # Calculate potential buys with current coins
        current_coins = state.current_player.coins
        desired_coins = self._get_desired_coins(state)
        
        # If we have enough coins for our desired purchase, we might want to save some treasures
        if current_coins >= desired_coins:
            return None
            
        # Otherwise play highest value treasure
        treasures = [(c.stats.coins, c) for c in valid_choices]
        treasures.sort(key=lambda x: x[0], reverse=True)
        return treasures[0][1]

    def choose_buy(self, state: GameState, choices: list[Optional[Card]]) -> Optional[Card]:
        """Choose a card to buy using improved purchase heuristics."""
        valid_choices = [c for c in choices if c is not None]
        if not valid_choices:
            return None
            
        # Calculate values and pair with cards
        values: list[Tuple[float, Card]] = []
        for card in valid_choices:
            value = self.get_buy_value(card, state)
            values.append((value, card))
            
        if not values:
            return None
            
        # Sort by value and return highest value card
        values.sort(key=lambda x: x[0], reverse=True)
        return values[0][1]

    def get_action_value(self, card: Card, state: GameState) -> float:
        """Calculate how valuable it is to play this action using improved heuristics."""
        value = self.strategy.play_priorities.get(card.name, 0.0)
        player = state.current_player
        
        # Key strategic adjustments
        if card.stats.actions > 0:  # Village effects
            action_cards_in_hand = sum(1 for c in player.hand if c.is_action)
            if player.actions <= 1 and action_cards_in_hand > 1:
                value += 3.0  # Highly prioritize villages when we need actions
                
        if card.stats.cards > 0:  # Card drawing
            value += card.stats.cards * 1.5  # Base value for card drawing
            
            # Extra value if our hand is running low
            if len(player.hand) <= 3:
                value += 2.0
                
        if card.stats.coins > 0:  # Treasure generating actions
            value += card.stats.coins * 1.0
            
            # Extra value if we're close to affording a key card
            desired_coins = self._get_desired_coins(state)
            if (player.coins + card.stats.coins) >= desired_coins > player.coins:
                value += 2.0
                
        if card.is_attack:  # Attack cards
            # More valuable in multiplayer games
            if len(state.players) > 2:
                value += 1.0
                
        # Adjust for timing
        value = self._adjust_for_game_stage(value, state)
            
        return value

    def get_buy_value(self, card: Card, state: GameState) -> float:
        """Calculate how valuable it is to buy this card using improved heuristics."""
        value = self.strategy.gain_priorities.get(card.name, 0.0)
        player = state.current_player
        
        # Count key cards in deck
        deck_size = (len(player.deck) + len(player.hand) + 
                    len(player.discard) + len(player.in_play))
        action_count = sum(1 for pile in [player.deck, player.hand, player.discard, player.in_play]
                         for c in pile if c.is_action)
        treasure_count = sum(1 for pile in [player.deck, player.hand, player.discard, player.in_play]
                           for c in pile if c.is_treasure)
        
        # Basic strategy adjustments
        if card.name == "Province":
            # Buy provinces more aggressively late game
            if state.supply["Province"] <= 4:
                value += 4.0
            # Don't buy too early
            if deck_size < 10:
                value -= 3.0
                
        elif card.name == "Duchy":
            # Buy duchies late game
            if state.supply["Province"] <= 5:
                value += 2.0
                
        elif card.name == "Estate":
            # Avoid estates unless nearing game end
            if state.supply["Province"] > 3:
                value -= 2.0
                
        elif card.name == "Gold":
            value += 2.0  # Always good
            if deck_size < 12:  # Extra early game value
                value += 1.0
                
        elif card.name == "Silver":
            if deck_size < 8:  # Good early
                value += 1.5
            else:
                value += 0.5
                
        # Action card adjustments
        if card.is_action:
            # Don't overload on actions
            action_ratio = action_count / max(1, deck_size)
            if action_ratio > 0.4:  # Too many actions
                value -= 2.0
            
            # Value engine components
            if card.stats.cards > 0 and card.stats.actions > 0:  # Laboratory effects
                value += 2.0
            elif card.stats.cards > 0:  # Card drawing
                value += 1.0
            elif card.stats.actions > 0:  # Village effects
                value += 1.0
                
            # Extra value for first few actions
            if action_count < 3:
                value += 1.0
                
        # Cost considerations
        value -= (card.cost.coins * 0.1)  # Slight bias towards cheaper cards
        
        # Game stage adjustments
        value = self._adjust_for_game_stage(value, state)
        
        return value

    def _get_desired_coins(self, state: GameState) -> int:
        """Determine how many coins we want for our next buy."""
        # Look for the most expensive affordable key card
        if state.supply.get("Province", 0) > 0 and state.current_player.coins >= 8:
            return 8
        elif state.supply.get("Gold", 0) > 0 and state.current_player.coins >= 6:
            return 6
        elif state.supply.get("Duchy", 0) > 0 and state.supply.get("Province", 0) <= 4:
            return 5
        elif state.supply.get("Silver", 0) > 0 and state.current_player.coins >= 3:
            return 3
        return 0

    def _adjust_for_game_stage(self, value: float, state: GameState) -> float:
        """Adjust card values based on game stage."""
        provinces_left = state.supply.get("Province", 0)
        empty_piles = sum(1 for count in state.supply.values() if count == 0)
        
        if provinces_left <= 2 or empty_piles >= 2:
            # Late game: favor victory points and coin generation
            if any(t in self.strategy.gain_priorities for t in ["Province", "Duchy", "Estate"]):
                value *= 1.5
            if any(t in self.strategy.gain_priorities for t in ["Gold", "Silver"]):
                value *= 1.3
        elif provinces_left <= 4:
            # Mid-late game: balance engine building with victory points
            pass
        else:
            # Early game: favor engine building
            if any(t in self.strategy.gain_priorities 
                  for t in ["Village", "Laboratory", "Market", "Festival"]):
                value *= 1.2
                
        return value

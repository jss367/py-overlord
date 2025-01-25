
# dominion/game/player_state.py
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from ..cards.base_card import Card
import random

@dataclass
class PlayerState:
    ai: 'AI'  # Type annotation as string to avoid circular import
    
    # Resources
    actions: int = 1
    buys: int = 1
    coins: int = 0
    potions: int = 0
    
    # Card collections
    hand: List[Card] = field(default_factory=list)
    deck: List[Card] = field(default_factory=list)
    discard: List[Card] = field(default_factory=list)
    in_play: List[Card] = field(default_factory=list)
    duration: List[Card] = field(default_factory=list)
    multiplied_durations: List[Card] = field(default_factory=list)
    
    # Turn tracking
    turns_taken: int = 0
    actions_played: int = 0

    def initialize(self):
        """Set up starting deck (7 Coppers, 3 Estates) and draw initial hand."""
        # Will implement once we have basic cards
        pass

    def draw_cards(self, count: int) -> List[Card]:
        """Draw specified number of cards from deck, shuffling if needed."""
        drawn = []
        
        while len(drawn) < count:
            # If deck is empty, shuffle discard pile
            if not self.deck and self.discard:
                self.shuffle_discard_into_deck()
            
            # Stop if no cards left
            if not self.deck:
                break
                
            # Draw a card
            card = self.deck.pop()
            drawn.append(card)
            self.hand.append(card)
            
        return drawn

    def shuffle_discard_into_deck(self):
        """Shuffle discard pile to create new deck."""
        self.deck = self.discard[:]
        random.shuffle(self.deck)
        self.discard = []

    def count_in_deck(self, card_name: str) -> int:
        """Count total copies of named card across all piles."""
        return sum(
            1 for card in (self.hand + self.deck + self.discard + self.in_play + self.duration)
            if card.name == card_name
        )

    def get_victory_points(self, game_state) -> int:
        """Calculate total victory points."""
        return sum(
            card.get_victory_points(self)
            for card in (self.hand + self.deck + self.discard + self.in_play + self.duration)
        )

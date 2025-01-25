
# dominion/game/game_state.py
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Callable
from collections import defaultdict
import random

from ..cards.base_card import Card, CardType
from .player_state import PlayerState

@dataclass
class GameState:
    players: List[PlayerState]
    supply: Dict[str, int] = field(default_factory=dict)
    trash: List[Card] = field(default_factory=list)
    current_player_index: int = 0
    phase: str = "start"
    turn_number: int = 1
    extra_turn: bool = False
    copper_value: int = 1

    def __post_init__(self):
        self.log_callback = lambda msg: print(msg)
        self.logs = []
        
    @property
    def current_player(self) -> PlayerState:
        return self.players[self.current_player_index]

    def initialize_game(self, players: List[PlayerState], kingdom_cards: List[Card]):
        """Set up the game with given players and kingdom cards."""
        self.players = players
        self.setup_supply(kingdom_cards)
        
        # Initialize players
        for player in self.players:
            player.initialize()

        self.log("Game initialized with players: " + 
                 ", ".join(str(p.ai) for p in self.players))
        self.log("Kingdom cards: " + 
                 ", ".join(c.name for c in kingdom_cards))

    def setup_supply(self, kingdom_cards: List[Card]):
        """Set up the initial supply piles."""
        self.supply = {}
        
        # Add basic cards (will implement specific counts later)
        basic_cards = ["Copper", "Silver", "Gold", "Estate", "Duchy", "Province"]
        for card_name in basic_cards:
            self.supply[card_name] = self.get_basic_card_count(card_name)
            
        # Add kingdom cards
        for card in kingdom_cards:
            self.supply[card.name] = card.starting_supply(self)

    def get_basic_card_count(self, card_name: str) -> int:
        """Get the starting count for basic cards based on player count."""
        n_players = len(self.players)
        
        if card_name == "Copper":
            return 60 - (7 * n_players)
        elif card_name == "Silver":
            return 40
        elif card_name == "Gold":
            return 30
        elif card_name in ["Estate", "Duchy"]:
            return 8 if n_players <= 2 else 12
        elif card_name == "Province":
            if n_players <= 2:
                return 8
            elif n_players <= 4:
                return 12
            return 15
        elif card_name == "Curse":
            return 10 * (n_players - 1)
            
        return 10  # Default for kingdom cards

    def play_turn(self):
        """Execute a single player's turn."""
        if self.phase == "start":
            self.handle_start_phase()
        elif self.phase == "action":
            self.handle_action_phase()
        elif self.phase == "treasure":
            self.handle_treasure_phase()
        elif self.phase == "buy":
            self.handle_buy_phase()
        elif self.phase == "cleanup":
            self.handle_cleanup_phase()

    def handle_start_phase(self):
        """Handle the start of turn phase."""
        if not self.extra_turn:
            self.current_player.turns_taken += 1
            self.log(f"\n== {self.current_player.ai}'s turn {self.current_player.turns_taken} ==")
        else:
            self.log(f"\n== {self.current_player.ai}'s extra turn ==")
            
        self.do_duration_phase()
        self.phase = "action"

    def do_duration_phase(self):
        """Handle duration effects at start of turn."""
        self.log("Duration phase started")
        player = self.current_player
        
        # Handle duration cards
        for card in player.duration[:]:
            self.log(f"{player.ai} resolves duration effect of {card}")
            card.on_duration(self)
            
        # Handle multiplied durations
        for card in player.multiplied_durations:
            self.log(f"{player.ai} resolves duration effect of {card} again")
            card.on_duration(self)
            
        player.multiplied_durations = []
        self.log("Duration phase ended")

    def log(self, message: str):
        """Log a game message."""
        self.logs.append(message)
        self.log_callback(message)

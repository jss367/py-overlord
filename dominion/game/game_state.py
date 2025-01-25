
# dominion/game/game_state.py
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Callable
from collections import defaultdict
import random
from ..cards.registry import get_card
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

    def initialize_game(self, ais: List['AI'], kingdom_cards: List[Card]):
        """Set up the game with given AIs and kingdom cards."""
        # Create PlayerState objects for each AI
        self.players = [PlayerState(ai) for ai in ais]
        self.setup_supply(kingdom_cards)
        
        # Initialize players
        for player in self.players:
            player.initialize()  # This now calls initialize on PlayerState, not AI

        self.log("Game initialized with players: " + 
                ", ".join(str(p.ai) for p in self.players))
        self.log("Kingdom cards: " + 
                ", ".join(c.name for c in kingdom_cards))

    def setup_supply(self, kingdom_cards: List[Card]):
        """Set up the initial supply piles."""
        self.supply = {}
        
        # Add basic cards with proper counts
        basic_cards = {
            "Copper": 60 - (7 * len(self.players)),  # Remove starting coppers
            "Silver": 40,
            "Gold": 30,
            "Estate": 12 if len(self.players) > 2 else 8,  # Adjust for player count
            "Duchy": 12 if len(self.players) > 2 else 8,
            "Province": 12 if len(self.players) > 2 else 8,
            "Curse": 10 * (len(self.players) - 1)
        }
        
        # Add basic cards to supply
        for card_name, count in basic_cards.items():
            self.supply[card_name] = count
            
        # Add kingdom cards
        for card in kingdom_cards:
            self.supply[card.name] = card.starting_supply(self)

        self.log(f"Supply initialized: {self.supply}")

    def is_game_over(self) -> bool:
        """Check if the game is over."""
        # Game ends if Province pile is empty
        if self.supply.get("Province", 0) == 0:
            self.log("Game over: Provinces depleted")
            return True
            
        # Or if any three supply piles are empty
        empty_piles = sum(1 for count in self.supply.values() if count == 0)
        if empty_piles >= 3:
            self.log("Game over: Three piles depleted")
            return True
            
        # Hard turn limit to prevent infinite games
        if self.turn_number > 100:
            self.log("Game over: Maximum turns reached")
            return True

        # Check if all players are truly stuck
        stuck_players = 0
        for player in self.players:
            if player_is_stuck(player):
                stuck_players += 1
        
        if stuck_players == len(self.players):
            self.log("Game over: All players truly stuck")
            return True

        return False

    def play_turn(self):
        """Execute a single player's turn."""
        if self.is_game_over():
            return

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

    def handle_action_phase(self):
        """Handle the action phase of a turn."""
        player = self.current_player
        
        while player.actions > 0:
            # Get playable action cards from hand
            action_cards = [card for card in player.hand if card.is_action]
            
            if not action_cards:
                self.log(f"{player.ai} has no more actions to play")
                break
                
            # Let AI choose an action
            choice = player.ai.choose_action(self, action_cards + [None])
            if choice is None:
                self.log(f"{player.ai} chooses not to play an action")
                break
                
            # Play the chosen action
            self.log(f"{player.ai} plays {choice}")
            player.actions -= 1
            player.actions_played += 1
            player.hand.remove(choice)
            player.in_play.append(choice)
            choice.on_play(self)
            
        self.phase = "treasure"

    def handle_treasure_phase(self):
        """Handle the treasure phase of a turn."""
        player = self.current_player
        
        while True:
            # Get playable treasures from hand
            treasures = [card for card in player.hand if card.is_treasure]
            
            if not treasures:
                self.log(f"{player.ai} has no more treasures to play")
                break
                
            # Let AI choose a treasure
            choice = player.ai.choose_treasure(self, treasures + [None])
            if choice is None:
                self.log(f"{player.ai} chooses not to play more treasures")
                break
                
            # Play the chosen treasure
            self.log(f"{player.ai} plays {choice}")
            player.hand.remove(choice)
            player.in_play.append(choice)
            choice.on_play(self)
            
        self.phase = "buy"

    def handle_buy_phase(self):
        """Handle the buy phase of a turn."""
        player = self.current_player
        
        while player.buys > 0:
            # Get affordable cards from supply
            affordable = []
            for card_name, count in self.supply.items():
                if count > 0:
                    card = get_card(card_name)
                    if (card.cost.coins <= player.coins and 
                        card.cost.potions <= player.potions and
                        card.may_be_bought(self)):
                        affordable.append(card)
            
            if not affordable:
                self.log(f"{player.ai} can't afford any cards")
                break
                
            # Let AI choose a card to buy
            choice = player.ai.choose_buy(self, affordable + [None])
            if choice is None:
                self.log(f"{player.ai} chooses not to buy")
                break
                
            # Buy the chosen card
            self.log(f"{player.ai} buys {choice}")
            player.buys -= 1
            player.coins -= choice.cost.coins
            player.potions -= choice.cost.potions
            self.supply[choice.name] -= 1
            
            # Move card to discard
            choice.on_buy(self)
            player.discard.append(choice)
            choice.on_gain(self, player)
            
        self.phase = "cleanup"

    def handle_cleanup_phase(self):
        """Handle the cleanup phase of a turn."""
        player = self.current_player
        
        # Discard hand and in-play cards
        player.discard.extend(player.hand)
        player.discard.extend(player.in_play)
        player.hand = []
        player.in_play = []
        
        # Draw new hand
        player.draw_cards(5)
        
        # Reset resources
        player.actions = 1
        player.buys = 1
        player.coins = 0
        player.potions = 0
        
        # Move to next player
        if not self.extra_turn:
            self.current_player_index = (self.current_player_index + 1) % len(self.players)
            if self.current_player_index == 0:
                self.turn_number += 1
                
        self.extra_turn = False
        self.phase = "start"






def player_is_stuck(player: PlayerState) -> bool:
    """
    Check if a player is stuck with no valid moves.
    A player is only stuck if they can't:
    1. Play any actions
    2. Play any treasures
    3. Buy any cards (including Copper)
    4. Draw any more cards
    """
    # Check if player can play actions
    has_actions = any(card.is_action for card in player.hand)
    
    # Check if player can play treasures
    has_treasures = any(card.is_treasure for card in player.hand)
    
    # Check if player can buy anything (including Copper)
    can_buy_copper = self.supply.get("Copper", 0) > 0
    
    # Check if player can draw more cards
    total_cards = (len(player.hand) + len(player.deck) + 
                len(player.discard) + len(player.in_play))
    has_cards_to_draw = total_cards > 0
    
    return not (has_actions or has_treasures or can_buy_copper or has_cards_to_draw)

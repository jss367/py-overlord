# dominion/cards/treasures.py
from .base_card import Card, CardCost, CardStats, CardType

class Copper(Card):
    def __init__(self):
        super().__init__(
            name="Copper",
            cost=CardCost(coins=0),
            stats=CardStats(coins=1),
            types=[CardType.TREASURE]
        )
    
    def starting_supply(self, game_state) -> int:
        return 60

class Silver(Card):
    def __init__(self):
        super().__init__(
            name="Silver",
            cost=CardCost(coins=3),
            stats=CardStats(coins=2),
            types=[CardType.TREASURE]
        )
    
    def starting_supply(self, game_state) -> int:
        return 40

class Gold(Card):
    def __init__(self):
        super().__init__(
            name="Gold",
            cost=CardCost(coins=6),
            stats=CardStats(coins=3),
            types=[CardType.TREASURE]
        )
    
    def starting_supply(self, game_state) -> int:
        return 30

# dominion/cards/base_card.py
from dataclasses import dataclass
from typing import Dict, Optional, List
from enum import Enum

@dataclass
class CardCost:
    coins: int = 0
    potions: int = 0

@dataclass
class CardStats:
    actions: int = 0
    cards: int = 0
    coins: int = 0
    buys: int = 0
    vp: int = 0
    potions: int = 0

class CardType(Enum):
    ACTION = "action"
    TREASURE = "treasure"
    VICTORY = "victory"
    CURSE = "curse"
    ATTACK = "attack"
    REACTION = "reaction"
    DURATION = "duration"

class Card:
    def __init__(self, name: str, cost: CardCost, stats: CardStats, types: List[CardType]):
        self.name = name
        self.cost = cost
        self.stats = stats
        self.types = types
    
    @property
    def is_action(self) -> bool:
        return CardType.ACTION in self.types

    @property
    def is_treasure(self) -> bool:
        return CardType.TREASURE in self.types
    
    @property
    def is_victory(self) -> bool:
        return CardType.VICTORY in self.types

    @property
    def is_attack(self) -> bool:
        return CardType.ATTACK in self.types

    @property
    def is_reaction(self) -> bool:
        return CardType.REACTION in self.types

    @property
    def is_duration(self) -> bool:
        return CardType.DURATION in self.types

    def get_victory_points(self, player) -> int:
        """Get victory points this card provides for the given player."""
        return self.stats.vp

    def starting_supply(self, game_state) -> int:
        """Get number of copies of this card in the supply at game start."""
        return 10

    def may_be_bought(self, game_state) -> bool:
        """Check if this card can currently be bought."""
        return True

    def on_play(self, game_state):
        """Execute this card's effects when played."""
        player = game_state.current_player
        player.actions += self.stats.actions
        player.coins += self.stats.coins
        player.potions += self.stats.potions
        player.buys += self.stats.buys
        
        if self.stats.cards > 0:
            game_state.draw_cards(player, self.stats.cards)
        
        # Let subclasses add additional effects
        self.play_effect(game_state)

    def play_effect(self, game_state):
        """Additional effects when card is played. Override in subclasses."""
        pass

    def on_buy(self, game_state):
        """Effects that happen when card is bought. Override in subclasses."""
        pass

    def on_gain(self, game_state, player):
        """Effects that happen when card is gained. Override in subclasses."""
        pass

    def on_trash(self, game_state, player):
        """Effects that happen when card is trashed. Override in subclasses."""
        pass

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"Card({self.name})"
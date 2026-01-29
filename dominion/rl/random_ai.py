"""Random AI opponent for training and evaluation."""

import random
from typing import Optional

from dominion.ai.base_ai import AI
from dominion.cards.base_card import Card
from dominion.game.game_state import GameState


class _RandomStrategy:
    """Stub strategy for compatibility with GameState logging."""
    name = "Random"


class RandomAI(AI):
    """AI that makes uniformly random valid choices.

    Used as a baseline opponent and for initial RL training.
    """

    def __init__(self):
        self.strategy = _RandomStrategy()

    @property
    def name(self) -> str:
        return "RandomAI"

    def choose_action(self, state: GameState, choices: list[Optional[Card]]) -> Optional[Card]:
        """Randomly choose an action from available choices."""
        return random.choice(choices)

    def choose_treasure(self, state: GameState, choices: list[Optional[Card]]) -> Optional[Card]:
        """Randomly choose a treasure from available choices."""
        return random.choice(choices)

    def choose_buy(self, state: GameState, choices: list[Optional[Card]]) -> Optional[Card]:
        """Randomly choose a card to buy from available choices."""
        return random.choice(choices)

    def choose_card_to_trash(self, state: GameState, choices: list[Card]) -> Optional[Card]:
        """Randomly choose a card to trash, or None to skip."""
        # Add None as option to allow skipping trash
        return random.choice(choices + [None])

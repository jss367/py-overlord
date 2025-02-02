from typing import List, Optional

from dominion.ai.base_ai import AI
from dominion.cards.base_card import Card
from dominion.game.game_state import GameState
from dominion.strategy.enhanced_strategy import EnhancedStrategy


class StrategyAI(AI):
    """AI that uses YAML-defined strategies"""

    def __init__(self, strategy: EnhancedStrategy):
        self.strategy = strategy
        self._name = f"{strategy.name}-AI"

    @property
    def name(self) -> str:
        return self._name

    def choose_action(self, state: GameState, choices: List[Optional[Card]]) -> Optional[Card]:
        valid_choices = [c for c in choices if c is not None]
        if not valid_choices:
            return None

        return self.strategy.choose_action(state, state.current_player, valid_choices)

    def choose_buy(self, state: GameState, choices: List[Optional[Card]]) -> Optional[Card]:
        valid_choices = [c for c in choices if c is not None]
        if not valid_choices:
            return None

        return self.strategy.choose_gain(state, state.current_player, valid_choices)

    def choose_treasure(self, state: GameState, choices: List[Optional[Card]]) -> Optional[Card]:
        valid_choices = [c for c in choices if c is not None and c.is_treasure]
        if not valid_choices:
            return None

        return self.strategy.choose_treasure(state, state.current_player, valid_choices)

    def choose_card_to_trash(self, state: GameState, choices: List[Card]) -> Optional[Card]:
        if not choices:
            return None

        return self.strategy.choose_trash(state, state.current_player, choices)

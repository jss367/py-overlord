from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from dominion.ai.base_ai import AI
from dominion.cards.base_card import Card
from dominion.strategy.enhanced_strategy import EnhancedStrategy

if TYPE_CHECKING:  # Avoid circular imports at runtime
    from dominion.game.game_state import GameState


class GeneticAI(AI):
    """AI that uses a learnable strategy with improved heuristics."""

    def __init__(self, strategy: EnhancedStrategy):
        self.strategy = strategy
        self._name = f"GeneticAI-{id(self)}"

    @property
    def name(self) -> str:
        return self._name

    def choose_action(self, state: GameState, choices: list[Optional[Card]]) -> Optional[Card]:
        valid_choices = [c for c in choices if c is not None]
        if not valid_choices:
            return None

        return self.strategy.choose_action(state, state.current_player, valid_choices)

    def choose_treasure(self, state: GameState, choices: list[Optional[Card]]) -> Optional[Card]:
        valid_choices = [c for c in choices if c is not None]
        if not valid_choices:
            return None

        return self.strategy.choose_treasure(state, state.current_player, valid_choices)

    def choose_buy(self, state: GameState, choices: list[Optional[Card]]) -> Optional[Card]:
        valid_choices = [c for c in choices if c is not None]
        if not valid_choices:
            return None

        return self.strategy.choose_gain(state, state.current_player, valid_choices)

    def choose_way(self, state: GameState, card: Card, ways: list) -> Optional[object]:
        if hasattr(self.strategy, 'choose_way'):
            return self.strategy.choose_way(state, state.current_player, card, ways)
        return None

    def choose_torturer_attack(self, state: GameState, player) -> bool:
        if hasattr(self.strategy, 'choose_torturer_response'):
            return self.strategy.choose_torturer_response(state, player)
        return super().choose_torturer_attack(state, player)

    def choose_card_to_trash(self, state: GameState, choices: list[Card]) -> Optional[Card]:
        if not choices:
            return None

        return self.strategy.choose_trash(state, state.current_player, choices)

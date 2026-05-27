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

        strategy_choices = (
            valid_choices
            if getattr(state, "_choosing_main_action_phase", False)
            else choices
        )
        return self.strategy.choose_action(state, state.current_player, strategy_choices)

    def choose_treasure(self, state: GameState, choices: list[Optional[Card]]) -> Optional[Card]:
        valid_choices = [c for c in choices if c is not None]
        if not valid_choices:
            return None

        return self.strategy.choose_treasure(state, state.current_player, valid_choices)

    def choose_buy(self, state: GameState, choices: list[Optional[Card]]) -> Optional[Card]:
        if not choices:
            return None

        return self.strategy.choose_gain(state, state.current_player, choices)

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

    def choose_watchtower_reaction(
        self, state: GameState, player, gained_card: Card
    ) -> Optional[str]:
        hook = getattr(self.strategy, "choose_watchtower_reaction", None)
        if hook is not None:
            return hook(state, player, gained_card)
        return super().choose_watchtower_reaction(state, player, gained_card)

    def choose_card_to_topdeck_for_clerk(
        self, state: GameState, player, choices: list[Card]
    ) -> Optional[Card]:
        hook = getattr(self.strategy, "choose_card_to_topdeck_for_clerk", None)
        if hook is not None:
            return hook(state, player, choices)
        return super().choose_card_to_topdeck_for_clerk(state, player, choices)

    def should_play_clerk_reaction(
        self, state: GameState, player, clerk: Card | None = None
    ) -> bool:
        hook = getattr(self.strategy, "should_play_clerk_reaction", None)
        if hook is not None:
            return bool(hook(state, player, clerk))
        return super().should_play_clerk_reaction(state, player, clerk)

    def choose_investment_mode(
        self, state: GameState, player, can_trash_treasure: bool
    ) -> str:
        hook = getattr(self.strategy, "choose_investment_mode", None)
        if hook is not None:
            return hook(state, player, can_trash_treasure)
        return super().choose_investment_mode(state, player, can_trash_treasure)

    def choose_treasure_to_trash_for_investment(
        self, state: GameState, player, choices: list[Card]
    ) -> Optional[Card]:
        hook = getattr(self.strategy, "choose_treasure_to_trash_for_investment", None)
        if hook is not None:
            return hook(state, player, choices)
        return super().choose_treasure_to_trash_for_investment(state, player, choices)

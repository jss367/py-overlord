"""Phase-aware strategy helpers.

Flat priority lists are useful for serialization and genetic mutation, but a
good Dominion plan usually changes shape over time: opening, building, adding
payload, and greening are different jobs. ``PhaseAwareStrategy`` keeps the old
``EnhancedStrategy`` API while allowing strategies to provide phase-specific
priority lists that override the global fallback lists.
"""

from __future__ import annotations

from enum import StrEnum

from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState
from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class StrategyPhase(StrEnum):
    OPENING = "opening"
    BUILD = "build"
    PAYLOAD = "payload"
    GREEN = "green"
    ENDGAME = "endgame"


class PhaseAwareStrategy(EnhancedStrategy):
    """EnhancedStrategy with optional phase-specific priorities."""

    def __init__(self) -> None:
        super().__init__()
        self.phase_gain_priority: dict[StrategyPhase, list[PriorityRule]] = {}
        self.phase_action_priority: dict[StrategyPhase, list[PriorityRule]] = {}

    def classify_phase(self, state: GameState, player: PlayerState) -> StrategyPhase:
        provinces_left = state.supply.get("Province", 0)
        empty_piles = getattr(state, "empty_piles", 0)

        if provinces_left <= 2 or empty_piles >= 2:
            return StrategyPhase.ENDGAME
        if provinces_left <= 4:
            return StrategyPhase.GREEN
        if state.turn_number <= 4:
            return StrategyPhase.OPENING

        action_count = sum(1 for card in player.all_cards() if getattr(card, "is_action", False))
        payload_count = sum(
            1
            for card in player.all_cards()
            if getattr(card, "is_treasure", False) and getattr(card, "cost", None) and card.cost.coins >= 6
        )
        if action_count >= 3 and payload_count < 2:
            return StrategyPhase.PAYLOAD
        return StrategyPhase.BUILD

    def choose_gain(self, state, player, choices):
        phase = self.classify_phase(state, player)
        phase_rules = self.phase_gain_priority.get(phase, [])
        result = self._choose_from_priority(phase_rules, choices, state, player, f"gain:{phase.value}")
        if result is not None:
            return result
        return super().choose_gain(state, player, choices)

    def choose_action(self, state, player, choices):
        phase = self.classify_phase(state, player)
        phase_rules = self.phase_action_priority.get(phase, [])
        result = self._choose_from_priority(phase_rules, choices, state, player, f"action:{phase.value}")
        if result is not None:
            return result
        return super().choose_action(state, player, choices)

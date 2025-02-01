from typing import Optional, List
from dominion.cards.base_card import Card
from dominion.game.game_state import GameState
from dominion.ai.base_ai import AI
from dominion.strategy.strategy_runner import StrategyRunner


class StrategyAI(AI):
    """AI that uses YAML-defined strategies"""

    def __init__(self, strategy_runner: StrategyRunner):
        self.runner = strategy_runner
        self._name = f"{strategy_runner.strategy.name}-AI"

    @property
    def name(self) -> str:
        return self._name

    def choose_action(
        self, state: GameState, choices: List[Optional[Card]]
    ) -> Optional[Card]:
        """Choose an action based on strategy"""
        valid_choices = [c for c in choices if c is not None]
        if not valid_choices:
            return None

        # Special handling for Rebuild
        rebuild_choices = [c for c in valid_choices if c.name == "Rebuild"]
        if rebuild_choices:
            if self.runner.should_play_rebuild(state, state.current_player):
                return rebuild_choices[0]
            return None

        # For other actions, play in order encountered
        return valid_choices[0]

    def choose_buy(
        self, state: GameState, choices: List[Optional[Card]]
    ) -> Optional[Card]:
        """Choose a buy based on strategy's gain priority"""
        valid_choices = [c for c in choices if c is not None]
        if not valid_choices:
            return None

        return self.runner.get_card_to_gain(state, state.current_player, valid_choices)

    def choose_treasure(
        self, state: GameState, choices: List[Optional[Card]]
    ) -> Optional[Card]:
        """Play treasures in descending order of value"""
        valid_choices = [c for c in choices if c is not None and c.is_treasure]
        if not valid_choices:
            return None
        return max(valid_choices, key=lambda c: c.stats.coins)

    def choose_card_to_trash(
        self, state: GameState, choices: List[Card]
    ) -> Optional[Card]:
        """For Rebuild, use rebuild priority. Otherwise use basic priority."""
        if not choices:
            return None

        # Check if this is for Rebuild
        if state.current_player.actions_played > 0:
            last_played = state.current_player.in_play[-1]
            if last_played.name == "Rebuild":
                return self.runner.get_rebuild_target(
                    state, state.current_player, choices
                )

        # Basic priority: Curse > Estate > Copper
        priority_order = ["Curse", "Estate", "Copper"]
        for card_name in priority_order:
            for card in choices:
                if card.name == card_name:
                    return card

        return None

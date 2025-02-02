from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState
from dominion.cards.base_card import Card


class StateWrapper:
    """Safe wrapper for GameState to use in condition evaluation"""

    def __init__(self, state: GameState):
        self._state = state

    def countInSupply(self, card_name: str) -> int:
        return self._state.supply.get(card_name, 0)

    def turn_number(self) -> int:
        return self._state.turn_number


class PlayerWrapper:
    """Safe wrapper for PlayerState to use in condition evaluation"""

    def __init__(self, player: PlayerState):
        self._player = player

    def countInDeck(self, card_name: str) -> int:
        return self._player.count_in_deck(card_name)

    def actions(self) -> int:
        return self._player.actions

    def coins(self) -> int:
        return self._player.coins


class StrategyRunner:
    """Executes strategy logic in the game context"""

    def __init__(self, strategy: "Strategy"):
        self.strategy = strategy

    def evaluate_condition(
        self, condition: str, state: GameState, player: PlayerState
    ) -> bool:
        """Safely evaluate a strategy condition"""
        if not condition:
            return True

        context = {"state": StateWrapper(state), "my": PlayerWrapper(player)}

        try:
            return eval(condition, {"__builtins__": {}}, context)
        except Exception as e:
            print(f"Error evaluating condition '{condition}': {e}")
            return False

    def should_play_rebuild(self, state: GameState, player: PlayerState) -> bool:
        """Check if Rebuild should be played according to strategy"""
        if not self.strategy.wants_to_rebuild:
            return True

        condition = self.strategy.wants_to_rebuild.get("condition")
        return self.evaluate_condition(condition, state, player)

    def get_card_to_gain(
        self, state: GameState, player: PlayerState, choices: list[Card]
    ) -> Card | None:
        """Get the highest priority card to gain from available choices"""
        choice_names = {c.name for c in choices}

        for priority in self.strategy.gain_priority:
            if priority.card in choice_names and self.evaluate_condition(
                priority.condition, state, player
            ):
                return next(c for c in choices if c.name == priority.card)

        return None

    def get_rebuild_target(
        self, state: GameState, player: PlayerState, choices: list[Card]
    ) -> Card | None:
        """Get the highest priority card to target with Rebuild"""
        if not self.strategy.rebuild_priority:
            return None

        choice_names = {c.name for c in choices}

        for priority in self.strategy.rebuild_priority:
            if priority.card in choice_names:
                return next(c for c in choices if c.name == priority.card)

        return None

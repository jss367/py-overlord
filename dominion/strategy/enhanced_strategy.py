from dataclasses import dataclass
from typing import Any, Optional

from dominion.cards.base_card import Card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState


@dataclass
class PriorityRule:
    """Represents a single priority rule in a strategy"""

    card_name: str
    condition: Optional[str] = None
    context: Optional[dict[str, Any]] = None


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

    def countInHand(self, card_name: str) -> int:
        return sum(1 for c in self._player.hand if c.name == card_name)

    def countInDeck(self, card_name: str) -> int:
        return self._player.count_in_deck(card_name)

    def actions(self) -> int:
        return self._player.actions

    def coins(self) -> int:
        return self._player.coins

    @property
    def hand_size(self) -> int:
        return len(self._player.hand)


class GameContext:
    """Provides safe access to game state for condition evaluation"""

    def __init__(self, state: GameState, player: PlayerState):
        self.state = state
        self.my = PlayerWrapper(player)

    def turn_number(self) -> int:
        return self.state.turn_number

    def provinces_left(self) -> int:
        return self.state.supply.get("Province", 0)

    def countInSupply(self, card_name: str) -> int:
        return self.state.supply.get(card_name, 0)


class EnhancedStrategy:
    """Enhanced strategy implementation supporting ordered rules with conditions"""

    def __init__(self):
        self.name: str = "Unnamed Strategy"
        self.action_priority: list[PriorityRule] = []
        self.gain_priority: list[PriorityRule] = []
        self.treasure_priority: list[PriorityRule] = []
        self.trash_priority: list[PriorityRule] = []

    @classmethod
    def from_yaml(cls, yaml_data: dict[str, Any]) -> 'EnhancedStrategy':
        """Create strategy from YAML configuration"""
        strategy = cls()

        if 'metadata' in yaml_data:
            strategy.name = yaml_data['metadata'].get('name', 'Unnamed Strategy')

        def parse_rules(rules_list):
            result = []
            for rule in rules_list:
                if isinstance(rule, dict):
                    result.append(
                        PriorityRule(
                            card_name=rule['card'], condition=rule.get('condition'), context=rule.get('context', {})
                        )
                    )
                else:
                    result.append(PriorityRule(card_name=rule))
            return result

        if 'actionPriority' in yaml_data:
            strategy.action_priority = parse_rules(yaml_data['actionPriority'])
        if 'gainPriority' in yaml_data:
            strategy.gain_priority = parse_rules(yaml_data['gainPriority'])
        if 'treasurePriority' in yaml_data:
            strategy.treasure_priority = parse_rules(yaml_data['treasurePriority'])
        if 'trashPriority' in yaml_data:
            strategy.trash_priority = parse_rules(yaml_data['trashPriority'])

        return strategy

    def evaluate_condition(self, rule: PriorityRule, state: GameState, player: PlayerState) -> bool:
        """Safely evaluate a rule's condition"""
        if not rule.condition:
            return True

        context = GameContext(state, player)
        try:
            # Create restricted globals for safe evaluation
            restricted_globals = {
                '__builtins__': {
                    'abs': abs,
                    'len': len,
                    'max': max,
                    'min': min,
                    'sum': sum,
                }
            }

            # Make context available to condition
            eval_locals = {'state': context, 'my': context.my}

            return bool(eval(rule.condition, restricted_globals, eval_locals))
        except Exception as e:
            print(f"Error evaluating condition '{rule.condition}': {e}")
            return False

    def choose_action(self, state: GameState, player: PlayerState, choices: list[Card]) -> Optional[Card]:
        """Choose an action card following priority rules"""
        choice_map = {card.name: card for card in choices if card}

        # Go through priority rules in order
        for rule in self.action_priority:
            if rule.card_name in choice_map and self.evaluate_condition(rule, state, player):
                return choice_map[rule.card_name]

        return None

    def choose_gain(self, state: GameState, player: PlayerState, choices: list[Card]) -> Optional[Card]:
        """Choose a card to gain following priority rules"""
        choice_map = {card.name: card for card in choices if card}

        for rule in self.gain_priority:
            if rule.card_name in choice_map and self.evaluate_condition(rule, state, player):
                return choice_map[rule.card_name]

        return None

    def choose_treasure(self, state: GameState, player: PlayerState, choices: list[Card]) -> Optional[Card]:
        """Choose a treasure card following priority rules"""
        choice_map = {card.name: card for card in choices if card}

        for rule in self.treasure_priority:
            if rule.card_name in choice_map and self.evaluate_condition(rule, state, player):
                return choice_map[rule.card_name]

        return None

    def choose_trash(self, state: GameState, player: PlayerState, choices: list[Card]) -> Optional[Card]:
        """Choose a card to trash following priority rules"""
        choice_map = {card.name: card for card in choices if card}

        for rule in self.trash_priority:
            if rule.card_name in choice_map and self.evaluate_condition(rule, state, player):
                return choice_map[rule.card_name]

        return None

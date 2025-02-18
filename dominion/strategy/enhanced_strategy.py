from dataclasses import dataclass
from typing import Any, Optional

from dominion.cards.base_card import Card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState
from dominion.strategy.condition_parser import ConditionParser, GameContext


@dataclass
class PriorityRule:
    """Represents a single priority rule in a strategy"""

    card_name: str
    condition: Optional[str] = None


class EnhancedStrategy:
    """Enhanced strategy implementation using the new condition parser"""

    def __init__(self):
        self.name: str = "Unnamed Strategy"
        self.action_priority: list[PriorityRule] = []
        self.gain_priority: list[PriorityRule] = []
        self.treasure_priority: list[PriorityRule] = []
        self.trash_priority: list[PriorityRule] = []
        self.condition_parser = ConditionParser()

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
                    result.append(PriorityRule(card_name=rule['card'], condition=rule.get('condition')))
                else:
                    # Handle simple string case for backward compatibility
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
        """Evaluate a rule's condition using the parser"""
        if not rule.condition:
            return True

        try:
            context = GameContext(state, player)
            condition_func = self.condition_parser.parse(rule.condition)
            return condition_func(context)
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

    def to_yaml(self) -> dict[str, Any]:
        """Convert strategy to YAML format"""
        yaml_data = {'metadata': {'name': self.name, 'version': '2.0'}}

        def convert_rules(rules):
            return [
                {'card': rule.card_name, 'condition': rule.condition} if rule.condition else rule.card_name
                for rule in rules
            ]

        if self.action_priority:
            yaml_data['actionPriority'] = convert_rules(self.action_priority)
        if self.gain_priority:
            yaml_data['gainPriority'] = convert_rules(self.gain_priority)
        if self.treasure_priority:
            yaml_data['treasurePriority'] = convert_rules(self.treasure_priority)
        if self.trash_priority:
            yaml_data['trashPriority'] = convert_rules(self.trash_priority)

        return yaml_data

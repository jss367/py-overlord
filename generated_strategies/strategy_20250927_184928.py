from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class Strategy20250927_184928(EnhancedStrategy):
    def __init__(self) -> None:
        super().__init__()
        self.name = 'gen0-140275150746544'
        self.description = "Evolved attack engine with Bridge, Ironmonger, and Barbarian"
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule('Bridge'),
            PriorityRule('Ironmonger'),
            PriorityRule('Marauder'),
            PriorityRule('Mill'),
            PriorityRule('Barbarian'),
            PriorityRule('Council Room'),
            PriorityRule('Giant'),
            PriorityRule('Mint'),
            PriorityRule('Tragic Hero', 'state.turn_number <= 5'),
            PriorityRule('Nobles'),
            PriorityRule('Copper'),
            PriorityRule('Silver'),
            PriorityRule('Gold'),
            PriorityRule('Estate'),
            PriorityRule('Duchy'),
            PriorityRule('Province'),
        ]

        self.action_priority = [
            PriorityRule('Bridge'),
            PriorityRule('Barbarian'),
            PriorityRule('Council Room'),
            PriorityRule('Giant'),
            PriorityRule('Mint'),
            PriorityRule('Tragic Hero'),
            PriorityRule('Nobles'),
        ]

        self.treasure_priority = [
            PriorityRule('Gold'),
            PriorityRule('Silver'),
            PriorityRule('Copper'),
        ]

        self.trash_priority = [
            PriorityRule('Curse'),
            PriorityRule('Estate', 'state.provinces_left > 4'),
            PriorityRule('Copper', 'my.count(Silver) + my.count(Gold) >= 3'),
        ]

def create_strategy20250927_184928() -> EnhancedStrategy:
    return Strategy20250927_184928()

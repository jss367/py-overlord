"""Island-model champion evolved from the ``Bilbao Anvil Feodum Slog`` seed.

Kept for the record: 12 generations, population 20, 16 games per evaluation,
panel of the three money seeds plus Big Money (78% vs the panel). Evolution
dropped the Gold and Estate rules and the late-Feodum rule, converging on the
same shape the hand search found; the published ``Bilbao Best Found`` beats
it 61-39 over 400 games. See ``reports/strategies/bilbao-strategy-guide.html``.
"""

from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


class BilbaoAnvilFeodumSlogChampion(EnhancedStrategy):
    def __init__(self) -> None:
        super().__init__()
        self.name = 'Bilbao Anvil Feodum Slog Champion'
        self.description = "Evolved Anvil/Feodum money: no Gold, no Estates, Feodum from six Silvers."
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule('Province'),
            PriorityRule('Duchy', PriorityRule.provinces_left('<=', 5)),
            PriorityRule('Anvil', PriorityRule.max_in_deck('Anvil', 3)),
            PriorityRule('Feodum', PriorityRule.has_cards(['Silver'], 6)),
            PriorityRule("Fool's Gold", PriorityRule.max_in_deck("Fool's Gold", 8)),
            PriorityRule('Silver'),
        ]

        self.action_priority = [
            PriorityRule('Wandering Minstrel'),
            PriorityRule('Wheelwright'),
            PriorityRule('Raider'),
        ]

        self.treasure_priority = [
            PriorityRule('Anvil'),
            PriorityRule('Gold'),
            PriorityRule("Fool's Gold"),
            PriorityRule('Silver'),
            PriorityRule('Copper'),
        ]

        self.trash_priority = [
            PriorityRule('Curse'),
            PriorityRule('Estate', PriorityRule.provinces_left('>', 4)),
            PriorityRule('Copper', PriorityRule.has_cards(['Silver', 'Gold'], 4)),
        ]

def create_bilbao_anvil_feodum_slog_champion() -> EnhancedStrategy:
    return BilbaoAnvilFeodumSlogChampion()
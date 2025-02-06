from pathlib import Path
from typing import Optional

import yaml

from dominion.simulation.genetic_trainer import GeneticTrainer
from dominion.simulation.strategy_battle import StrategyBattle
from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule
from dominion.strategy.strategy_loader import StrategyLoader


def convert_to_priority_rules(priority_list: list) -> list[PriorityRule]:
    """Convert a list of priority dictionaries to PriorityRule objects."""
    rules = []
    for item in priority_list:
        if isinstance(item, dict):
            rules.append(
                PriorityRule(card_name=item['card'], condition=item.get('condition'), context=item.get('context', {}))
            )
        else:
            # Handle simple string entries
            rules.append(PriorityRule(card_name=item))
    return rules


def train_optimal_strategy():
    """Main function to train an optimal strategy, building on existing optimal strategy if it exists"""
    kingdom_cards = [
        "Village",
        "Smithy",
        "Market",
        "Festival",
        "Laboratory",
        "Mine",
        "Witch",
        "Moat",
        "Workshop",
        "Chapel",
    ]

    # Set up paths
    strategies_dir = Path("strategies")
    strategies_dir.mkdir(exist_ok=True)
    optimal_strategy_path = strategies_dir / "optimal_strategy.yaml"

    # Load existing optimal strategy if it exists
    existing_optimal = None
    if optimal_strategy_path.exists():
        try:
            with open(optimal_strategy_path, 'r') as f:
                yaml_data = yaml.safe_load(f)
                if yaml_data:
                    # Handle case where strategy is the root
                    strategy_data = yaml_data.get('strategy', yaml_data)

                    # Create new EnhancedStrategy
                    existing_optimal = EnhancedStrategy()

                    # Set name if exists
                    if 'metadata' in strategy_data:
                        existing_optimal.name = strategy_data['metadata'].get('name', 'Unnamed Strategy')

                    # Convert each priority list if it exists
                    if 'gainPriority' in strategy_data:
                        existing_optimal.gain_priority = convert_to_priority_rules(strategy_data['gainPriority'])

                    if 'actionPriority' in strategy_data:
                        existing_optimal.action_priority = convert_to_priority_rules(strategy_data['actionPriority'])

                    if 'treasurePriority' in strategy_data:
                        existing_optimal.treasure_priority = convert_to_priority_rules(
                            strategy_data['treasurePriority']
                        )

                    if 'trashPriority' in strategy_data:
                        existing_optimal.trash_priority = convert_to_priority_rules(strategy_data['trashPriority'])

                    if 'discardPriority' in strategy_data:
                        existing_optimal.discard_priority = convert_to_priority_rules(strategy_data['discardPriority'])

                    print("\nLoaded existing optimal strategy")
        except Exception as e:
            print(f"\nError loading existing optimal strategy: {e}")

    # Create trainer with existing optimal strategy in initial population
    trainer = GeneticTrainer(
        kingdom_cards=kingdom_cards,
        population_size=5,
        generations=4,
        mutation_rate=0.1,
        games_per_eval=4,
        log_folder="optimal_strategy_logs",
    )

    # If we have an existing optimal strategy, inject it
    if existing_optimal:
        trainer.inject_strategy(existing_optimal)

    print("\nStarting training process...")
    new_strategy, metrics = trainer.train()

    # Convert new strategy to EnhancedStrategy if needed
    if isinstance(new_strategy, dict):
        strategy_data = new_strategy.get('strategy', new_strategy)
        new_strategy_obj = EnhancedStrategy()

        if 'metadata' in strategy_data:
            new_strategy_obj.name = strategy_data['metadata'].get('name', 'Unnamed Strategy')

        for priority_type in ['gainPriority', 'actionPriority', 'treasurePriority', 'trashPriority', 'discardPriority']:
            if priority_type in strategy_data:
                setattr(
                    new_strategy_obj,
                    priority_type.replace('Priority', '_priority'),
                    convert_to_priority_rules(strategy_data[priority_type]),
                )

        new_strategy = new_strategy_obj

    if existing_optimal:
        # Battle new strategy against existing optimal
        battle = StrategyBattle(kingdom_cards)
        battle_name = f"gen{trainer.current_generation}-best"
        results = battle.run_battle(battle_name, "optimal_strategy", num_games=20)

        if results["strategy1_win_rate"] > 55:
            print(f"\nNew strategy superior! Win rate vs old: {results['strategy1_win_rate']:.1f}%")
            save_strategy = new_strategy
        else:
            print(f"\nNew strategy not superior. Win rate vs old: {results['strategy1_win_rate']:.1f}%")
            save_strategy = existing_optimal
    else:
        save_strategy = new_strategy

    # Convert strategy to YAML format
    strategy_yaml = {'strategy': {'metadata': {'name': 'optimal_strategy'}}}

    # Add each priority list that exists
    for attr, yaml_key in [
        ('gain_priority', 'gainPriority'),
        ('action_priority', 'actionPriority'),
        ('treasure_priority', 'treasurePriority'),
        ('trash_priority', 'trashPriority'),
        ('discard_priority', 'discardPriority'),
    ]:
        priority_list = getattr(save_strategy, attr, None)
        if priority_list:
            strategy_yaml['strategy'][yaml_key] = [
                {'card': rule.card_name, 'condition': rule.condition} for rule in priority_list
            ]

    # Save strategy
    with open(optimal_strategy_path, 'w') as f:
        yaml.dump(strategy_yaml, f, sort_keys=False)

    print(f"\nFinal strategy win rate vs BigMoney: {metrics['win_rate']:.1f}%")
    print("\nOptimal Strategy priorities:")
    print(yaml.dump(strategy_yaml['strategy'].get('gainPriority', []), indent=2))

    return save_strategy, metrics


if __name__ == "__main__":
    train_optimal_strategy()

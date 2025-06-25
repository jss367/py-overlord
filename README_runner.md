# Dominion Strategy Runner

This runner trains Dominion strategies using a genetic algorithm approach. It automatically saves the best strategy as a Python class file.

## Usage

### Basic Usage (Default Kingdom Cards)

```bash
python runner.py
```

### Using Command Line Kingdom Cards

```bash
python runner.py --kingdom-cards Village Smithy Market Festival Laboratory
```

### Using YAML Configuration File

```bash
python runner.py --config basic_kingdom.yaml
```

### Custom Training Parameters

```bash
python runner.py --population-size 20 --generations 25 --mutation-rate 0.15 --games-per-eval 15
```

### Combined Usage

```bash
python runner.py --config kingdom_config.yaml --population-size 30 --generations 50
```

## Command Line Arguments

- `--kingdom-cards`: List of kingdom cards to use for training
- `--config` or `-c`: YAML configuration file containing kingdom cards and training parameters
- `--population-size`: Population size for genetic algorithm (default: 5)
- `--generations`: Number of generations to run (default: 10)
- `--mutation-rate`: Mutation rate (default: 0.1)
- `--games-per-eval`: Number of games to play per strategy evaluation (default: 10)

## YAML Configuration Format

```yaml
# Basic format
kingdom_cards:
  - "Village"
  - "Smithy"
  - "Market"
  # ... more cards

# Optional training parameters
training_parameters:
  population_size: 20
  generations: 25
  mutation_rate: 0.15
  games_per_eval: 15
```

## Output

The runner will:

1. Train a strategy using genetic algorithms
2. Display the training progress and results
3. Show the best strategy's card priorities
4. Automatically save the strategy as a Python class in `generated_strategies/strategy_YYYYMMDD_HHMMSS.py`

## Example Output Files

Generated strategy files will look like:

```python
from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule

class Strategy20240101_120000(EnhancedStrategy):
    def __init__(self) -> None:
        super().__init__()
        self.name = "gen9-4567890123"
        self.description = "Auto-generated strategy from genetic training"
        self.version = "1.0"

        self.gain_priority = [
            PriorityRule("Province"),
            PriorityRule("Gold"),
            # ... more rules
        ]

        # ... other priorities

def create_strategy20240101_120000() -> EnhancedStrategy:
    return Strategy20240101_120000()
```

from datetime import datetime
from dominion.strategies.strategy import Strategy

def create_big_money_strategy() -> Strategy:
    """Create a basic Big Money strategy."""
    strategy = Strategy()
    
    # Set metadata
    strategy.name = "Pure Big Money"
    strategy.description = "Classic Big Money strategy focusing on treasure acquisition. Aims to get Gold as quickly as possible, then starts buying Provinces."
    strategy.version = "1.0"
    strategy.creation_date = datetime.now().strftime("%Y-%m-%d")
    
    # Gain priorities - what to buy
    strategy.gain_priorities = {
        # Treasures (high priority)
        "Gold": 0.95,    # Highest priority when affordable
        "Silver": 0.85,  # Strong early game priority
        "Copper": 0.1,   # Very low priority - avoid buying
        
        # Victory cards (situational priority)
        "Province": 0.9,  # High priority when we can afford it
        "Duchy": 0.3,    # Low priority until late game
        "Estate": 0.0,   # Never buy additional Estates
        
        # Action cards (minimal priority in pure big money)
        "Village": 0.1,
        "Smithy": 0.2,   # Slightly higher as it could be situationally useful
        "Market": 0.3,    # Modest priority due to +1 Card, +1 Coin
        "Festival": 0.2,
        "Laboratory": 0.25,
        "Mine": 0.15,
        "Witch": 0.2,
        "Moat": 0.1,
        "Workshop": 0.1,
        "Chapel": 0.4     # Higher priority as it helps thin the deck
    }
    
    # Play priorities - what to play when in hand
    strategy.play_priorities = {
        # Always play treasures
        "Gold": 1.0,
        "Silver": 0.95,
        "Copper": 0.9,
        
        # Play actions if we have them
        "Village": 0.5,
        "Smithy": 0.7,    # Higher priority as it draws cards
        "Market": 0.8,    # High priority due to no drawback
        "Festival": 0.7,
        "Laboratory": 0.8,
        "Mine": 0.6,
        "Witch": 0.7,
        "Moat": 0.6,
        "Workshop": 0.5,
        "Chapel": 0.95    # Very high priority - use it when available
    }
    
    # Strategy weights
    strategy.action_weight = 0.2   # Low weight on actions
    strategy.treasure_weight = 0.9  # Very high weight on treasures
    strategy.victory_weight = 0.4   # Moderate weight on victory cards
    strategy.engine_weight = 0.1    # Very low weight on engine building

    return strategy

if __name__ == "__main__":
    # Create the strategy
    big_money = create_big_money_strategy()
    
    # Save it to the strategies directory
    big_money.save("strategies/big_money.json")
    
    print(f"Created and saved {big_money.name} strategy")
    print(f"Description: {big_money.description}")

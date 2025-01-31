from typing import Optional
from dominion.cards.base_card import Card
from dominion.game.game_state import GameState
from dominion.strategies.strategy import Strategy
from dominion.ai.base_ai import AI

class GeneticAI(AI):
    """AI that uses a learnable strategy with improved heuristics."""

    def __init__(self, strategy: Strategy):
        self.strategy = strategy
        self._name = f"GeneticAI-{id(self)}"

    @property
    def name(self) -> str:
        return self._name

    def choose_action(
        self, state: GameState, choices: list[Optional[Card]]
    ) -> Optional[Card]:
        """Choose an action card to play using improved action sequencing."""
        valid_choices = [c for c in choices if c is not None]
        if not valid_choices:
            return None

        # Calculate values and pair with cards
        values: list[tuple[float, Card]] = []
        for card in valid_choices:
            value = self.get_action_value(card, state)
            values.append((value, card))

        if not values:
            return None

        # Sort by value and return highest value card
        values.sort(key=lambda x: x[0], reverse=True)
        return values[0][1] if values[0][0] > 0 else None

    def choose_treasure(
        self, state: GameState, choices: list[Optional[Card]]
    ) -> Optional[Card]:
        """Choose a treasure card to play."""
        # Always play treasures in descending order of value
        valid_choices = [c for c in choices if c is not None and c.is_treasure]
        if not valid_choices:
            return None

        # Sort by coin value and play highest first
        treasures = [(c.stats.coins, c) for c in valid_choices]
        treasures.sort(key=lambda x: x[0], reverse=True)
        return treasures[0][1]  # Always play highest value treasure

    def choose_buy(
        self, state: GameState, choices: list[Optional[Card]]
    ) -> Optional[Card]:
        """Choose a card to buy using improved strategy."""
        available_coins = state.current_player.coins
        valid_choices = [
            c for c in choices if c is not None and c.cost.coins <= available_coins
        ]

        if not valid_choices:
            return None

        # Calculate values and pair with cards
        values: list[tuple[float, Card]] = []
        for card in valid_choices:
            value = self.get_buy_value(card, state)
            values.append((value, card))

        if not values:
            return None

        # Sort by value and return highest value card
        values.sort(key=lambda x: x[0], reverse=True)
        return values[0][1] if values[0][0] > 0 else None

    def get_action_value(self, card: Card, state: GameState) -> float:
        """Calculate how valuable it is to play this action."""
        value = self.strategy.play_priorities.get(card.name, 0.0)
        player = state.current_player

        # Base values for card effects
        value += card.stats.actions * 2.0  # Actions are valuable
        value += card.stats.cards * 1.5  # Card draw is valuable
        value += card.stats.coins * 1.0  # Direct coins
        value += card.stats.buys * 0.5  # Extra buys

        # Situational bonuses
        if card.stats.actions > 0 and len([c for c in player.hand if c.is_action]) > 1:
            value += 2.0  # Village effects more valuable with other actions

        if len(player.hand) <= 2:
            value += card.stats.cards * 1.0  # Card draw more valuable with small hand

        if card.name == "Chapel":
            if self.should_trash_cards(state):
                value += 3.0  # High priority early game

        return value

    def get_buy_value(self, card: Card, state: GameState) -> float:
        """Calculate how valuable it is to buy this card."""
        value = 0.0
        player = state.current_player

        # Never buy Curse
        if card.name == "Curse":
            return -10.0

        # Early game priorities
        if state.turn_number <= 5:
            if card.name == "Chapel":
                return 8.0  # Highest early priority
            elif card.name == "Silver":
                return 7.0  # Second highest early priority

        # Basic treasure values
        if card.name == "Gold":
            value += 6.0
        elif card.name == "Silver":
            value += 4.0
        elif card.name == "Copper":
            value = -1.0  # Actively avoid buying copper

        # Victory card strategy
        provinces_left = state.supply.get("Province", 0)
        if card.name == "Province":
            if player.coins >= 8:
                value += 10.0  # Buy Province if we can afford it
        elif card.name == "Duchy":
            if provinces_left <= 4:
                value += 6.0  # Buy Duchy late game
        elif card.name == "Estate":
            if provinces_left <= 2:
                value += 4.0  # Buy Estate very late game
            else:
                value -= 2.0  # Otherwise avoid Estates

        return value

    def get_early_game_action_value(self, card: Card) -> float:
        """Value actions for early game engine building."""
        value = 0.0

        # Key early game cards
        if card.name == "Chapel":
            value += 8.0  # Best early game card
        elif card.name == "Laboratory":
            value += 7.0  # Strong card draw
        elif card.name == "Village":
            value += 6.0  # Actions are important
        elif card.name == "Smithy":
            value += 5.5  # Good card draw
        elif card.name == "Market":
            value += 5.0  # Good all-around card
        elif card.name == "Festival":
            value += 4.5  # Good actions and coins
        elif card.name == "Workshop":
            value += 4.0  # Good early game

        return value

    def get_late_game_action_value(self, card: Card, state: GameState) -> float:
        """Value actions for mid/late game."""
        value = 0.0

        # Adjust values based on what we already have
        action_cards = sum(1 for c in state.current_player.deck if c.is_action)

        if action_cards < 5:  # Still building engine
            value += card.stats.cards * 1.5
            value += card.stats.actions * 1.0
            value += card.stats.coins * 0.5
        else:  # Engine built, focus on payload
            value += card.stats.coins * 1.5
            value += card.stats.cards * 1.0
            value += card.stats.buys * 0.5

        return value

    def should_trash_cards(self, state: GameState) -> bool:
        """Determine if we should be aggressively trashing cards."""
        player = state.current_player

        # Count total treasure value
        total_treasure = sum(
            c.stats.coins
            for c in player.deck + player.hand + player.discard
            if c.is_treasure
        )

        # Count number of copper and estates
        coppers = sum(
            1 for c in player.deck + player.hand + player.discard if c.name == "Copper"
        )
        estates = sum(
            1 for c in player.deck + player.hand + player.discard if c.name == "Estate"
        )

        # Early game trashing
        if state.turn_number <= 10:
            return coppers > 4 or estates > 2

        # Mid game trashing
        return coppers > 2 and total_treasure >= 10

from typing import Optional, Tuple
from .base_ai import AI
from dominion.cards.base_card import Card
from dominion.game.game_state import GameState
from dominion.strategies.strategy import Strategy


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
        values: list[Tuple[float, Card]] = []
        for card in valid_choices:
            value = self.get_action_value(card, state)
            values.append((value, card))

        if not values:
            return None

        # Sort by value and return highest value card
        values.sort(key=lambda x: x[0], reverse=True)
        return values[0][1]

    def choose_treasure(
        self, state: GameState, choices: list[Optional[Card]]
    ) -> Optional[Card]:
        """Choose a treasure card to play."""
        valid_choices = [c for c in choices if c is not None and c.is_treasure]
        if not valid_choices:
            return None

        # Always play treasures - basic Big Money strategy
        treasures = [(c.stats.coins, c) for c in valid_choices]
        treasures.sort(key=lambda x: x[0], reverse=True)
        return treasures[0][1]

    def choose_buy(
        self, state: GameState, choices: list[Optional[Card]]
    ) -> Optional[Card]:
        """Choose a card to buy using basic Big Money strategy."""
        valid_choices = [
            c
            for c in choices
            if c is not None and c.cost.coins <= state.current_player.coins
        ]
        if not valid_choices:
            return None

        # Calculate values and pair with cards
        values: list[Tuple[float, Card]] = []
        for card in valid_choices:
            value = self.get_buy_value(card, state)
            values.append((value, card))

        if not values:
            return None

        # Sort by value and return highest value card
        values.sort(key=lambda x: x[0], reverse=True)
        return values[0][1]

    def get_action_value(self, card: Card, state: GameState) -> float:
        """Calculate how valuable it is to play this action using improved heuristics."""
        value = self.strategy.play_priorities.get(card.name, 0.0)
        player = state.current_player

        # Key strategic adjustments
        if card.stats.actions > 0:  # Village effects
            action_cards_in_hand = sum(1 for c in player.hand if c.is_action)
            if player.actions <= 1 and action_cards_in_hand > 1:
                value += 3.0  # Highly prioritize villages when we need actions

        if card.stats.cards > 0:  # Card drawing
            value += card.stats.cards * 1.5  # Base value for card drawing

            # Extra value if our hand is running low
            if len(player.hand) <= 3:
                value += 2.0

        if card.stats.coins > 0:  # Treasure generating actions
            value += card.stats.coins * 1.0

            # Extra value if we're close to affording a key card
            desired_coins = self._get_desired_coins(state)
            if (player.coins + card.stats.coins) >= desired_coins > player.coins:
                value += 2.0

        if card.is_attack:  # Attack cards
            # More valuable in multiplayer games
            if len(state.players) > 2:
                value += 1.0

        # Adjust for timing
        value = self._adjust_for_game_stage(value, state)

        return value

    def get_buy_value(self, card: Card, state: GameState) -> float:
        """Calculate how valuable it is to buy this card."""
        value = self.strategy.gain_priorities.get(card.name, 0.0)
        player = state.current_player

        # Basic Big Money priorities
        if card.name == "Gold":
            value += 4.0  # Highest priority for basic treasures
        elif card.name == "Silver":
            value += 3.0  # Second priority
        elif card.name == "Copper":
            value += 0.1  # Very low priority for Copper

        # Victory card priorities
        if card.name == "Province":
            if player.coins >= 8:  # If we can afford it, high priority
                value += 5.0
        elif card.name == "Duchy":
            # Buy Duchies late game
            if state.supply["Province"] <= 4:
                value += 3.0
        elif card.name == "Estate":
            # Generally avoid Estates unless end game
            if state.supply["Province"] > 2:
                value -= 2.0

        # Never buy Curses
        if card.name == "Curse":
            value -= 10.0

        return value

    def _get_desired_coins(self, state: GameState) -> int:
        """Determine target coins for buying."""
        if state.supply.get("Province", 0) > 0:
            return 8  # Always try to get to Province cost
        elif state.supply.get("Gold", 0) > 0:
            return 6  # Otherwise aim for Gold
        elif state.supply.get("Duchy", 0) > 0 and state.supply.get("Province", 0) <= 4:
            return 5  # Buy Duchies late game
        elif state.supply.get("Silver", 0) > 0:
            return 3  # Otherwise aim for Silver
        return 0  # Fallback

    def _adjust_for_game_stage(self, value: float, state: GameState) -> float:
        """Adjust card values based on game stage."""
        provinces_left = state.supply.get("Province", 0)
        empty_piles = sum(1 for count in state.supply.values() if count == 0)

        if provinces_left <= 2 or empty_piles >= 2:
            # Late game: favor victory points and coin generation
            if any(
                t in self.strategy.gain_priorities
                for t in ["Province", "Duchy", "Estate"]
            ):
                value *= 1.5
            if any(t in self.strategy.gain_priorities for t in ["Gold", "Silver"]):
                value *= 1.3
        elif provinces_left <= 4:
            # Mid-late game: balance engine building with victory points
            pass
        else:
            # Early game: favor engine building
            if any(
                t in self.strategy.gain_priorities
                for t in ["Village", "Laboratory", "Market", "Festival"]
            ):
                value *= 1.2

        return value

from typing import Optional
from dominion.cards.base_card import Card
from dominion.game.game_state import GameState
from dominion.strategy.strategy import Strategy
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
        """Calculate how valuable it is to play this action with phase-based considerations."""
        value = self.strategy.play_priorities.get(card.name, 0.0)
        player = state.current_player

        # Early game value (turns 1-5)
        if state.turn_number <= 5:
            value += self.get_early_game_action_value(card)

        elif state.turn_number > 15 or state.supply.get("Province", 8) <= 4:
            value += self.get_late_game_action_value(card, state)

        else:
            # Base values for card effects
            value += card.stats.actions * 2.0  # Actions are valuable
            value += card.stats.cards * 1.5  # Card draw is valuable
            value += card.stats.coins * 1.0  # Direct coins
            value += card.stats.buys * 0.5  # Extra buys

            # Engine building considerations
            action_cards_in_hand = len([c for c in player.hand if c.is_action])
            if card.stats.actions > 0:
                if action_cards_in_hand > 1:
                    value += 2.0  # Village effects more valuable with other actions
                if action_cards_in_hand > 2:
                    value += 1.0  # Even more valuable with multiple actions

            # Card draw value adjustments
            if len(player.hand) <= 2:
                value += (
                    card.stats.cards * 1.0
                )  # Card draw more valuable with small hand
            elif len(player.hand) >= 7:
                value -= card.stats.cards * 0.5  # Less valuable with large hand

            # Special card considerations
            if card.name == "Chapel" and self.should_trash_cards(state):
                value += 3.0  # High priority for deck thinning
            elif card.name == "Witch" and not any(
                any(c.name == "Moat" for c in p.hand)
                for p in state.players
                if p != state.current_player
            ):
                value += 2.0  # Attack more valuable if opponent can't block
            elif card.name == "Mine" and any(c.name == "Copper" for c in player.hand):
                value += 1.5  # More valuable with Copper to upgrade

        # Universal adjustments
        total_cards = len(player.deck) + len(player.hand) + len(player.discard)
        if total_cards < 10:  # Small deck
            value += card.stats.cards * 0.5  # Card draw more valuable
            if card.name == "Chapel":
                value -= 1.0  # Less need for trashing

        # Consider available actions
        if player.actions == 1:  # Last action
            if card.stats.actions == 0:  # Terminal action
                # Reduce value if we have other actions in hand we want to play
                remaining_actions = [
                    c for c in player.hand if c != card and c.is_action
                ]
                value -= len(remaining_actions) * 0.5

        return value

    def get_buy_value(self, card: Card, state: GameState) -> float:
        """Calculate how valuable it is to buy this card with phase-based strategy."""
        value = 0.0
        player = state.current_player

        # Never buy Curse
        if card.name == "Curse":
            return -10.0

        # Early game (turns 1-5)
        if state.turn_number <= 5:
            if card.name == "Chapel":
                return 8.0  # Highest early priority
            elif card.name == "Silver":
                return 7.0  # Second highest early priority
            elif card.is_action:
                # Value engine components highly early
                action_count = sum(
                    1 for c in player.deck + player.hand + player.discard if c.is_action
                )
                if action_count < 3:  # First few actions are valuable
                    if card.stats.actions > 0:  # Villages
                        value += 6.0
                    elif card.stats.cards >= 2:  # Card draw
                        value += 5.5
                    else:
                        value += 4.0

        # Mid game
        else:
            # Count key card types in deck
            all_cards = player.deck + player.hand + player.discard
            action_count = sum(1 for c in all_cards if c.is_action)
            treasure_value = sum(c.stats.coins for c in all_cards if c.is_treasure)
            village_count = sum(1 for c in all_cards if c.stats.actions > 0)
            terminal_count = sum(
                1 for c in all_cards if c.is_action and c.stats.actions == 0
            )

            # Engine building considerations
            if action_count < 8:  # Still building engine
                if card.stats.actions > 0:  # Villages
                    value += max(0, (terminal_count - village_count) * 1.5)
                elif card.stats.cards >= 2:  # Card draw
                    value += 5.0 - (action_count * 0.3)  # Less valuable as we get more
                elif card.name == "Market":  # Flexible cards
                    value += 4.0

            # Treasure considerations
            if card.is_treasure:
                if card.name == "Gold":
                    value += 6.0
                elif card.name == "Silver":
                    value += 4.0 - (
                        treasure_value * 0.1
                    )  # Less valuable as we get richer
                elif card.name == "Copper":
                    value = -1.0  # Actively avoid buying copper

            # Victory card timing strategy
            provinces_left = state.supply.get("Province", 0)
            if card.name == "Province":
                if player.coins >= 8:
                    # Buy Province if we can afford it, but consider engine strength
                    if action_count >= 5 or treasure_value >= 12:
                        value += 10.0
                    else:
                        value += 8.0  # Slightly lower priority if engine isn't ready
            elif card.name == "Duchy":
                if provinces_left <= 4:
                    value += 6.0  # Buy Duchy late game
                elif provinces_left <= 6:
                    value += 3.0  # Consider Duchy in mid-late game
            elif card.name == "Estate":
                if provinces_left <= 2:
                    value += 4.0  # Buy Estate very late game
                else:
                    value -= 2.0  # Otherwise avoid Estates

            # Attack card considerations
            if card.is_attack and not any(c.name == "Witch" for c in all_cards):
                value += 3.0  # Value first attack card

        # Factor in cost efficiency
        if card.cost.coins > 0:
            value = value * (
                1.0 + (1.0 / card.cost.coins)
            )  # Slight bonus for cheaper cards

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
            bool(c.name == "Copper") for c in player.deck + player.hand + player.discard
        )
        estates = sum(
            bool(c.name == "Estate") for c in player.deck + player.hand + player.discard
        )

        # Early game trashing
        if state.turn_number <= 10:
            return coppers > 4 or estates > 2

        # Mid game trashing
        return coppers > 2 and total_treasure >= 10

    def choose_card_to_trash(
        self, state: GameState, choices: list[Card]
    ) -> Optional[Card]:
        """Choose a card to trash from the available choices."""
        if not choices:
            return None

        # Calculate trash priority for each card
        trash_values: list[tuple[float, Card]] = []
        for card in choices:
            value = self._get_trash_value(card, state)
            trash_values.append((value, card))

        # Sort by value (higher value = more worth trashing)
        trash_values.sort(key=lambda x: x[0], reverse=True)

        # Only trash if the value exceeds our threshold
        return trash_values[0][1] if trash_values[0][0] > 0 else None

    def _get_trash_value(self, card: Card, state: GameState) -> float:
        """Calculate how valuable it is to trash this card."""
        player = state.current_player

        # Check game phase
        early_game = state.turn_number <= 10

        # Basic cards to trash
        if card.name == "Curse":
            return 10.0  # Always trash Curses
        elif card.name == "Copper":
            # Value trashing Copper based on economy
            total_treasure = sum(
                c.stats.coins
                for c in player.deck + player.hand + player.discard
                if c.is_treasure
            )
            copper_count = sum(
                1
                for c in player.deck + player.hand + player.discard
                if c.name == "Copper"
            )
            if early_game or copper_count > 4:
                return 8.0 if total_treasure >= 6 else 4.0
        elif card.name == "Estate":
            provinces_left = state.supply.get("Province", 0)
            if early_game or provinces_left > 4:
                return 6.0  # Aggressively trash early Estates
            return -1.0  # Keep Estates late game

        # Don't trash other cards
        return -5.0

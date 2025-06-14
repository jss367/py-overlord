from dataclasses import dataclass, field

from dominion.cards.base_card import Card
from dominion.cards.registry import get_card
from dominion.game.player_state import PlayerState


@dataclass
class GameState:
    players: list[PlayerState]
    supply: dict[str, int] = field(default_factory=dict)
    trash: list[Card] = field(default_factory=list)
    current_player_index: int = 0
    phase: str = "start"
    turn_number: int = 1
    extra_turn: bool = False
    copper_value: int = 1

    def __post_init__(self):
        """Initialize with default logger that prints to console."""
        self.logger = None
        self.log_callback = self._default_log_handler
        self.logs = []

    def set_logger(self, logger):
        """Set the game logger instance."""
        self.logger = logger
        self.log_callback = self._log_handler

    def _default_log_handler(self, message: str):
        """Default handler that just prints to console."""
        print(message)
        self.logs.append(message)

    def _log_handler(self, message):
        """Handle different types of log messages."""
        if isinstance(message, tuple):
            msg_type = message[0]
            if msg_type == "turn_header":
                # (turn_header, player_name, turn_number, resources)
                self.logger.log_turn_header(message[1], message[2], message[3])
            elif msg_type == "action":
                # (action, player_name, action_str, context)
                self.logger.log_action(message[1], message[2], message[3])
            elif msg_type == "supply_change":
                # (supply_change, card_name, count, remaining)
                self.logger.log_supply_change(message[1], message[2], message[3])
        else:
            # Legacy string message support
            if self.logger and self.logger.should_log_to_file:
                self.logger.file_logger.info(message)
            print(message)
            self.logs.append(message)

    @property
    def current_player(self) -> PlayerState:
        return self.players[self.current_player_index]

    def initialize_game(
        self, ais: list, kingdom_cards: list[Card], use_shelters: bool = False
    ):
        """Set up the game with given AIs and kingdom cards."""
        # Create PlayerState objects for each AI
        self.players = [PlayerState(ai) for ai in ais]
        self.setup_supply(kingdom_cards)

        # Initialize players
        for player in self.players:
            player.initialize(use_shelters)

        # Create a more readable player list for logging
        player_descriptions = []
        for player in self.players:
            # Access the strategy name from the AI's strategy
            # Get the full ID number from the AI name
            ai_id = player.ai.name.split('-')[1]
            # Take last 4 digits to ensure uniqueness
            short_id = ai_id[-4:]
            strategy_name = getattr(player.ai.strategy, 'name', 'Unknown Strategy')
            player_descriptions.append(f"Player {short_id} ({strategy_name})")

        self.log_callback("Game initialized with players: " + ", ".join(player_descriptions))
        self.log_callback("Kingdom cards: " + ", ".join(c.name for c in kingdom_cards))

    def setup_supply(self, kingdom_cards: list[Card]):
        """Set up the initial supply piles."""
        # Add basic cards with proper counts
        basic_cards = {
            "Copper": 60 - (7 * len(self.players)),
            "Silver": 40,
            "Gold": 30,
            "Estate": 12 if len(self.players) > 2 else 8,
            "Duchy": 12 if len(self.players) > 2 else 8,
            "Province": 12 if len(self.players) > 2 else 8,
            "Curse": 10 * (len(self.players) - 1),
        }

        self.supply = dict(basic_cards)
        # Add kingdom cards
        for card in kingdom_cards:
            self.supply[card.name] = card.starting_supply(self)

        self.log_callback(f"Supply initialized: {self.supply}")

    def handle_start_phase(self):
        """Handle the start of turn phase."""
        if not self.extra_turn:
            self.current_player.turns_taken += 1

        # Reset per-turn flags
        self.current_player.ignore_action_bonuses = False
        self.current_player.collection_played = 0

        # Log turn header with complete state
        resources = {
            "actions": self.current_player.actions,
            "buys": self.current_player.buys,
            "coins": self.current_player.coins,
            "hand": [card.name for card in self.current_player.hand],
        }
        self.log_callback(
            (
                "turn_header",
                self.current_player.ai.name,
                self.current_player.turns_taken,
                resources,
            )
        )

        # Only log duration phase if there are duration cards
        if self.current_player.duration:
            self.do_duration_phase()

        self.phase = "action"

    def do_duration_phase(self):
        """Handle effects of duration cards from previous turn."""
        player = self.current_player

        # Process duration cards that were played last turn
        for card in player.duration[:]:
            # Log duration card effect
            self.log_callback(("action", player.ai.name, f"resolves duration effect of {card}", {}))

            # Apply duration effects
            card.on_duration(self)

            # Move to discard after duration effect resolves
            player.duration.remove(card)
            player.discard.append(card)

        # Process any cards that were multiplied (e.g. by Throne Room)
        for card in player.multiplied_durations[:]:
            self.log_callback(
                (
                    "action",
                    player.ai.name,
                    f"resolves multiplied duration effect of {card}",
                    {},
                )
            )
            card.on_duration(self)

            player.multiplied_durations.remove(card)
            player.discard.append(card)

    def handle_action_phase(self):
        """Handle the action phase of a turn."""
        player = self.current_player

        while player.actions > 0:
            action_cards = [card for card in player.hand if card.is_action]

            if not action_cards:
                break

            choice = player.ai.choose_action(self, action_cards + [None])
            if choice is None:
                break

            # Update metrics for actions played
            if self.logger:
                self.logger.current_metrics.actions_played[player.ai.name] = (
                    self.logger.current_metrics.actions_played.get(player.ai.name, 0) + 1
                )
                self.logger.current_metrics.cards_played[choice.name] = (
                    self.logger.current_metrics.cards_played.get(choice.name, 0) + 1
                )

            # Log action play with context
            context = {
                "remaining_actions": player.actions - 1,
                "hand": [c.name for c in player.hand if c != choice],
            }
            self.log_callback(("action", player.ai.name, f"plays {choice}", context))

            player.actions -= 1
            player.actions_played += 1
            player.hand.remove(choice)
            player.in_play.append(choice)
            choice.on_play(self)

        self.phase = "treasure"

    def handle_treasure_phase(self):
        """Handle the treasure phase of a turn."""
        player = self.current_player

        while True:
            treasures = [card for card in player.hand if card.is_treasure]
            if not treasures:
                break

            choice = player.ai.choose_treasure(self, treasures + [None])
            if choice is None:
                break

            # Update metrics for treasures played
            if self.logger:
                self.logger.current_metrics.cards_played[choice.name] = (
                    self.logger.current_metrics.cards_played.get(choice.name, 0) + 1
                )

            # Log treasure play with context
            context = {
                "coins_before": player.coins,
                "coins_added": choice.stats.coins,
                "coins_after": player.coins + choice.stats.coins,
                "remaining_treasures": [c.name for c in player.hand if c != choice and c.is_treasure],
            }
            self.log_callback(("action", player.ai.name, f"plays {choice}", context))

            player.hand.remove(choice)
            player.in_play.append(choice)
            choice.on_play(self)

        self.phase = "buy"

    def handle_buy_phase(self):
        """Handle the buy phase of a turn."""
        player = self.current_player

        while player.buys > 0:
            affordable = [c for c in self._get_affordable_cards(player) if c is not None]

            if not affordable:
                break

            choice = player.ai.choose_buy(self, affordable + [None])
            if choice is None:
                break

            # Update metrics for cards bought
            if self.logger:
                self.logger.current_metrics.cards_bought[choice.name] = (
                    self.logger.current_metrics.cards_bought.get(choice.name, 0) + 1
                )

            # Log buy with context
            context = {
                "cost": choice.cost.coins,
                "remaining_coins": player.coins - choice.cost.coins,
                "remaining_buys": player.buys - 1,
            }
            self.log_callback(("action", player.ai.name, f"buys {choice}", context))

            # Update supply
            self.supply[choice.name] -= 1
            self.log_callback(("supply_change", choice.name, -1, self.supply[choice.name]))

            # Complete purchase
            player.buys -= 1
            player.coins -= choice.cost.coins
            player.discard.append(choice)
            choice.on_buy(self)
            choice.on_gain(self, player)

        self.phase = "cleanup"

    def _get_affordable_cards(self, player):
        """Helper to get list of affordable cards."""
        affordable = []
        for card_name, count in self.supply.items():
            if count > 0:
                card = get_card(card_name)
                if card.cost.coins <= player.coins and card.cost.potions <= player.potions and card.may_be_bought(self):
                    affordable.append(card)
        return affordable

    def _complete_purchase(self, player, card):
        """Helper to complete a card purchase."""
        player.buys -= 1
        player.coins -= card.cost.coins
        player.potions -= card.cost.potions
        self.supply[card.name] -= 1

        card.on_buy(self)
        player.discard.append(card)
        card.on_gain(self, player)

    def handle_cleanup_phase(self):
        """Handle the cleanup phase of a turn."""
        player = self.current_player

        # Discard hand and in-play cards
        player.discard.extend(player.hand)
        player.discard.extend(player.in_play)
        player.hand = []
        player.in_play = []

        # Draw new hand
        player.draw_cards(5)

        # Reset resources
        player.actions = 1
        player.buys = 1
        player.coins = 0
        player.potions = 0
        player.ignore_action_bonuses = False
        player.collection_played = 0

        # Move to next player
        if not self.extra_turn:
            self.current_player_index = (self.current_player_index + 1) % len(self.players)
            if self.current_player_index == 0:
                self.turn_number += 1

        self.extra_turn = False
        self.phase = "start"

    def play_turn(self):
        """Execute a single player's turn."""
        if self.is_game_over():
            return

        if self.phase == "start":
            self.handle_start_phase()
        elif self.phase == "action":
            self.handle_action_phase()
        elif self.phase == "treasure":
            self.handle_treasure_phase()
        elif self.phase == "buy":
            self.handle_buy_phase()
        elif self.phase == "cleanup":
            self.handle_cleanup_phase()

    def is_game_over(self) -> bool:
        """Check if the game is over.

        The game ends if:
        1. Province pile is empty
        2. Any three supply piles are empty
        3. Maximum turns (100) reached to prevent infinite games

        Returns:
            bool: True if the game is over, False otherwise
        """
        # Update turn count in metrics
        if self.logger:
            self.logger.current_metrics.turn_count = self.turn_number

        # Check win conditions in order of precedence

        # 1. Province pile empty
        if self.supply.get("Province", 0) == 0:
            self._update_final_metrics()
            self.log_callback("Game over: Provinces depleted")
            return True

        # 2. Three supply piles empty
        empty_piles = sum(1 for count in self.supply.values() if count == 0)
        if empty_piles >= 3:
            self._update_final_metrics()
            self.log_callback("Game over: Three piles depleted")
            return True

        # 3. Hard turn limit
        if self.turn_number > 100:
            self._update_final_metrics()
            self.log_callback("Game over: Maximum turns reached")
            return True

        return False

    def player_is_stuck(self, player: PlayerState) -> bool:
        """Check if a player is stuck with no valid moves."""
        has_actions = any(card.is_action for card in player.hand)
        has_treasures = any(card.is_treasure for card in player.hand)
        can_buy_copper = self.supply.get("Copper", 0) > 0

        total_cards = len(player.hand) + len(player.deck) + len(player.discard) + len(player.in_play)
        has_cards_to_draw = total_cards > 0

        return not (has_actions or has_treasures or can_buy_copper or has_cards_to_draw)

    def draw_cards(self, player: PlayerState, count: int) -> list[Card]:
        """Draw cards for a player, delegating to the player's draw_cards method."""
        return player.draw_cards(count)

    def give_curse_to_player(self, player):
        """Give a curse card to a player. GameState has access to registry so can create cards."""
        from ..cards.registry import get_card  # Import here to avoid circular dependency

        if self.supply.get("Curse", 0) > 0:
            curse = get_card("Curse")
            player.discard.append(curse)
            self.supply["Curse"] -= 1
            curse.on_gain(self, player)
            return True
        return False

    def _update_final_metrics(self):
        """Update final game metrics including victory points."""
        if not self.logger:
            return

        # Calculate and store final victory points for each player
        for player in self.players:
            vp = player.get_victory_points(self)
            self.logger.current_metrics.victory_points[player.ai.name] = vp

from dataclasses import dataclass, field
from typing import List, Dict

from ..cards.registry import get_card
from ..cards.base_card import Card
from .player_state import PlayerState


@dataclass
class GameState:
    players: List[PlayerState]
    supply: Dict[str, int] = field(default_factory=dict)
    trash: List[Card] = field(default_factory=list)
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

    def initialize_game(self, ais: list, kingdom_cards: List[Card]):
        """Set up the game with given AIs and kingdom cards."""
        # Create PlayerState objects for each AI
        self.players = [PlayerState(ai) for ai in ais]
        self.setup_supply(kingdom_cards)

        # Initialize players
        for player in self.players:
            player.initialize()

        self.log_callback(
            "Game initialized with players: "
            + ", ".join(str(p.ai) for p in self.players)
        )
        self.log_callback("Kingdom cards: " + ", ".join(c.name for c in kingdom_cards))

    def setup_supply(self, kingdom_cards: List[Card]):
        """Set up the initial supply piles."""
        self.supply = {}

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

        # Add basic cards to supply
        for card_name, count in basic_cards.items():
            self.supply[card_name] = count

        # Add kingdom cards
        for card in kingdom_cards:
            self.supply[card.name] = card.starting_supply(self)

        self.log_callback(f"Supply initialized: {self.supply}")

    def handle_start_phase(self):
        """Handle the start of turn phase."""
        if not self.extra_turn:
            self.current_player.turns_taken += 1

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

            # Log action play with context
            context = {
                "remaining_actions": player.actions - 1,
                "hand": [c.name for c in player.hand if c != choice],
            }
            self.log_callback(("action", player.ai.name, f"plays {choice}", context))

            # Update metrics
            if self.logger:
                self.logger.current_metrics.actions_played[player.ai.name] = (
                    self.logger.current_metrics.actions_played.get(player.ai.name, 0)
                    + 1
                )
                self.logger.current_metrics.cards_played[choice.name] = (
                    self.logger.current_metrics.cards_played.get(choice.name, 0) + 1
                )

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

            # Log treasure play with context
            context = {
                "coins_gained": choice.stats.coins,
                "total_coins": player.coins + choice.stats.coins,
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
            affordable = self._get_affordable_cards(player)

            if not affordable:
                break

            choice = player.ai.choose_buy(self, affordable + [None])
            if choice is None:
                break

            # Log buy with context
            context = {
                "cost": choice.cost.coins,
                "remaining_coins": player.coins - choice.cost.coins,
                "remaining_buys": player.buys - 1,
            }
            self.log_callback(("action", player.ai.name, f"buys {choice}", context))

            # Log supply change
            self.log_callback(
                ("supply_change", choice.name, -1, self.supply[choice.name] - 1)
            )

            # Update metrics
            if self.logger:
                self.logger.current_metrics.cards_bought[choice.name] = (
                    self.logger.current_metrics.cards_bought.get(choice.name, 0) + 1
                )

            self._complete_purchase(player, choice)

        self.phase = "cleanup"

    def _get_affordable_cards(self, player):
        """Helper to get list of affordable cards."""
        affordable = []
        for card_name, count in self.supply.items():
            if count > 0:
                card = get_card(card_name)
                if (
                    card.cost.coins <= player.coins
                    and card.cost.potions <= player.potions
                    and card.may_be_bought(self)
                ):
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

        # Move to next player
        if not self.extra_turn:
            self.current_player_index = (self.current_player_index + 1) % len(
                self.players
            )
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
        """Check if the game is over."""
        # Game ends if Province pile is empty
        if self.supply.get("Province", 0) == 0:
            self.log_callback("Game over: Provinces depleted")
            return True

        # Or if any three supply piles are empty
        empty_piles = sum(1 for count in self.supply.values() if count == 0)
        if empty_piles >= 3:
            self.log_callback("Game over: Three piles depleted")
            return True

        # Hard turn limit to prevent infinite games
        if self.turn_number > 100:
            self.log_callback("Game over: Maximum turns reached")
            return True

        # Check if all players are truly stuck
        stuck_players = 0
        for player in self.players:
            if self.player_is_stuck(player):
                stuck_players += 1

        if stuck_players == len(self.players):
            self.log_callback("Game over: All players truly stuck")
            return True

        return False

    def player_is_stuck(self, player: PlayerState) -> bool:
        """Check if a player is stuck with no valid moves."""
        has_actions = any(card.is_action for card in player.hand)
        has_treasures = any(card.is_treasure for card in player.hand)
        can_buy_copper = self.supply.get("Copper", 0) > 0

        total_cards = (
            len(player.hand)
            + len(player.deck)
            + len(player.discard)
            + len(player.in_play)
        )
        has_cards_to_draw = total_cards > 0

        return not (has_actions or has_treasures or can_buy_copper or has_cards_to_draw)

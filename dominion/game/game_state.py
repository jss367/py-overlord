import random
from dataclasses import dataclass, field
from typing import Optional

from dominion.cards.base_card import Card
from dominion.cards.registry import get_all_card_names, get_card
from dominion.cards.split_pile import SplitPileMixin
from dominion.game.player_state import PlayerState


@dataclass
class GameState:
    players: list[PlayerState]
    supply: dict[str, int] = field(default_factory=dict)
    black_market_deck: list[str] = field(default_factory=list)
    trash: list[Card] = field(default_factory=list)
    events: list = field(default_factory=list)
    projects: list = field(default_factory=list)
    ways: list = field(default_factory=list)
    current_player_index: int = 0
    phase: str = "start"
    turn_number: int = 1
    extra_turn: bool = False
    copper_value: int = 1
    trade_route_tokens_on_piles: dict[str, bool] = field(default_factory=dict)
    trade_route_mat_tokens: int = 0
    baker_in_supply: bool = False
    hex_deck: list[str] = field(default_factory=list)
    hex_discard: list[str] = field(default_factory=list)
    wild_hunt_pile_tokens: int = 0
    farmers_market_pile_tokens: int = 0
    temple_pile_tokens: int = 0
      

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
            elif msg_type == "turn_summary":
                # (turn_summary, player_name, actions_played, cards_bought, coins_available)
                self.logger.log_turn_summary(message[1], message[2], message[3], message[4])
        else:
            # Legacy string message support
            if self.logger:
                # Only write to file logger if enabled; avoid stdout spam
                if self.logger.should_log_to_file:
                    self.logger.file_logger.info(message)
            else:
                print(message)
            self.logs.append(message)

    @property
    def current_player(self) -> PlayerState:
        return self.players[self.current_player_index]

    def initialize_game(
        self,
        ais: list,
        kingdom_cards: list[Card],
        use_shelters: bool = False,
        events: list = None,
        projects: list = None,
        ways: list = None,
    ):
        """Set up the game with given AIs and kingdom cards."""
        # Create PlayerState objects for each AI
        self.players = [PlayerState(ai) for ai in ais]
        self.setup_supply(kingdom_cards)
        self.events = events or []
        self.projects = projects or []
        self.ways = ways or []

        # Initialize players
        for player in self.players:
            player.initialize(use_shelters)

        if self.baker_in_supply:
            for player in self.players:
                player.coin_tokens += 1

        # Create a more readable player list for logging
        player_descriptions = []
        for idx, player in enumerate(self.players, start=1):
            if self.logger:
                friendly = self.logger.format_player_name(player.ai.name)
            else:
                strategy_name = getattr(player.ai.strategy, 'name', 'Unknown Strategy')
                friendly = f"Player {idx} ({strategy_name})"
            player_descriptions.append(friendly)

        self.log_callback("Game initialized with players: " + ", ".join(player_descriptions))
        self.log_callback("Kingdom cards: " + ", ".join(c.name for c in kingdom_cards))

    def setup_supply(self, kingdom_cards: list[Card]):
        """Set up the initial supply piles."""
        # Add basic cards with proper counts
        copper_card = get_card("Copper")
        silver_card = get_card("Silver")
        gold_card = get_card("Gold")
        estate_card = get_card("Estate")
        duchy_card = get_card("Duchy")
        province_card = get_card("Province")
        curse_card = get_card("Curse")

        copper_supply = copper_card.starting_supply(self) - (7 * len(self.players))

        basic_cards = {
            "Copper": max(0, copper_supply),
            "Silver": silver_card.starting_supply(self),
            "Gold": gold_card.starting_supply(self),
            "Estate": estate_card.starting_supply(self),
            "Duchy": duchy_card.starting_supply(self),
            "Province": province_card.starting_supply(self),
            "Curse": max(0, curse_card.starting_supply(self)),
        }

        self.supply = dict(basic_cards)
        self.baker_in_supply = False
        # Add kingdom cards
        for card in kingdom_cards:
            self.supply[card.name] = card.starting_supply(self)

            # Automatically add split pile partner cards
            if isinstance(card, SplitPileMixin):
                partner = get_card(card.partner_card_name)
                if partner.name not in self.supply:
                    self.supply[partner.name] = partner.starting_supply(self)

            extras = card.get_additional_piles()
            for name, count in extras.items():
                if name not in self.supply:
                    self.supply[name] = count

            if card.name == "Baker":
                self.baker_in_supply = True

        if any(card.name == "Trade Route" for card in kingdom_cards):
            self.trade_route_tokens_on_piles = {}
            self.trade_route_mat_tokens = 0
            for name in self.supply:
                card = get_card(name)
                if card.is_victory:
                    self.trade_route_tokens_on_piles[name] = True
        else:
            self.trade_route_tokens_on_piles = {}
            self.trade_route_mat_tokens = 0

        if any(card.name == "Black Market" for card in kingdom_cards):
            self._prepare_black_market_deck(kingdom_cards)
        else:
            self.black_market_deck = []

    def _prepare_black_market_deck(self, kingdom_cards: list[Card]) -> None:
        """Build and shuffle the Black Market deck for this game."""

        supply_names = set(self.supply.keys())
        deck: list[str] = []
        for name in get_all_card_names():
            if name in supply_names:
                continue
            try:
                card = get_card(name)
            except ValueError:
                continue
            if getattr(card, "is_event", False) or getattr(card, "is_project", False):
                continue
            if card.name in {"Copper", "Silver", "Gold", "Estate", "Duchy", "Province", "Curse", "Platinum", "Colony"}:
                continue
            if card.name in {"Horse", "Spoils", "Ruins"}:
                continue
            deck.append(card.name)
        random.shuffle(deck)
        self.black_market_deck = deck

        self.log_callback(f"Supply initialized: {self.supply}")

    @property
    def empty_piles(self) -> int:
        """Return number of empty supply piles, counting split piles once."""
        counted: set[str] = set()
        empties = 0
        for name in list(self.supply.keys()):
            if name in counted:
                continue
            card = get_card(name)
            if isinstance(card, SplitPileMixin):
                partner = card.partner_card_name
                counted.add(name)
                counted.add(partner)
                if self.supply.get(name, 0) == 0 and self.supply.get(partner, 0) == 0:
                    empties += 1
            else:
                counted.add(name)
                if self.supply.get(name, 0) == 0:
                    empties += 1
        return empties

    def handle_start_phase(self):
        """Handle the start of turn phase."""
        player = self.current_player
        player.turns_taken += 1
        player.gained_five_last_turn = player.gained_five_this_turn
        player.gained_five_this_turn = False

        # Reset per-turn flags
        player.ignore_action_bonuses = False
        player.collection_played = 0
        player.goons_played = 0
        player.merchant_guilds_played = 0
        player.cost_reduction = 0
        player.innovation_used = False
        player.groundskeeper_bonus = 0
        player.crossroads_played = 0
        player.fools_gold_played = 0
        player.walled_villages_played = 0
        player.actions_gained_this_turn = 0
        player.cauldron_triggered = False
        player.cards_gained_this_turn = 0
        player.gained_victory_this_buy_phase = False
        player.flagship_pending = [
            card for card in player.flagship_pending if card in player.duration
        ]
        player.highwayman_blocked_this_turn = False
        player.actions_this_turn = 0
        player.bought_this_turn = []
        player.coins_spent_this_turn = 0
        player.banned_buys = []
        player.topdeck_gains = False
        player.charm_next_buy_copies = 0
        player.cannot_buy_actions = False
        player.envious_effect_active = False
        player.insignia_active = False
        player.fortune_doubled_this_turn = False

        # Return any cards delayed by the Delay event
        if self.current_player.delayed_cards:
            self.current_player.hand.extend(self.current_player.delayed_cards)
            self.current_player.delayed_cards = []

        # Resolve project effects that occur at the start of the turn
        for project in self.current_player.projects:
            project.on_turn_start(self, self.current_player)

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

            # Move to discard after duration effect resolves unless it stays in play
            if not getattr(card, "duration_persistent", False):
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
            if not getattr(card, "duration_persistent", False):
                player.discard.append(card)

    def handle_action_phase(self):
        """Handle the action phase of a turn."""
        player = self.current_player

        while True:
            action_cards = [card for card in player.hand if card.is_action]

            if not action_cards:
                break

            if player.actions == 0:
                if player.villagers > 0:
                    player.villagers -= 1
                    player.actions += 1
                    self.log_callback(
                        (
                            "action",
                            player.ai.name,
                            "spends a Villager for +1 Action",
                            {"villagers_remaining": player.villagers},
                        )
                    )
                else:
                    break

            choice = player.ai.choose_action(self, action_cards + [None])
            if choice is None:
                break

            way = None
            if self.ways:
                way = player.ai.choose_way(self, choice, self.ways + [None])

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
            action_desc = f"plays {choice}"
            if way:
                action_desc += f" using {way.name}"
            self.log_callback(("action", player.ai.name, action_desc, context))

            player.actions -= 1
            player.actions_played += 1
            player.actions_this_turn += 1
            player.hand.remove(choice)
            player.in_play.append(choice)
            if way:
                way.apply(self, choice)
            else:
                flagships_to_resolve: list[Card] = []
                pending_flagships = getattr(player, "flagship_pending", [])
                if pending_flagships and not getattr(choice, "is_command", False):
                    flagships_to_resolve = list(pending_flagships)
                    pending_flagships.clear()
                    for flagship in flagships_to_resolve:
                        if flagship in player.duration:
                            player.duration.remove(flagship)

                plays = 1 + len(flagships_to_resolve)
                for _ in range(plays):
                    choice.on_play(self)

        self.phase = "treasure"

    def _handle_start_of_buy_phase_effects(self) -> None:
        """Apply state effects that trigger at the start of the buy phase."""

        player = self.current_player
        player.cannot_buy_actions = False
        player.envious_effect_active = False
        player.cards_gained_this_buy_phase = 0
        player.gained_victory_this_buy_phase = False

        if player.deluded:
            player.deluded = False
            player.cannot_buy_actions = True

        if player.envious:
            player.envious = False
            player.envious_effect_active = True

    def handle_treasure_phase(self):
        """Handle the treasure phase of a turn."""
        player = self.current_player

        self._handle_start_of_buy_phase_effects()

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

            coins_before = player.coins
            player.hand.remove(choice)
            player.in_play.append(choice)

            blocked = (
                getattr(player, "highwayman_attacks", 0) > 0
                and not getattr(player, "highwayman_blocked_this_turn", False)
            )
            if blocked:
                player.highwayman_blocked_this_turn = True
                coins_after = player.coins
            else:
                choice.on_play(self)
                coins_after = player.coins
                if (
                    player.envious_effect_active
                    and choice.name in {"Silver", "Gold"}
                    and coins_after > coins_before + 1
                ):
                    player.coins = coins_before + 1
                    coins_after = player.coins

            remaining = [c.name for c in player.hand if c.is_treasure]
            context = {
                "coins_before": coins_before,
                "coins_added": coins_after - coins_before,
                "coins_after": coins_after,
                "remaining_treasures": remaining,
            }
            self.log_callback(("action", player.ai.name, f"plays {choice}", context))

        self.phase = "buy"

    def handle_buy_phase(self):
        """Handle the buy phase of a turn."""
        player = self.current_player

        while True:
            if player.debt > 0:
                if player.coins > 0:
                    paid = min(player.debt, player.coins)
                    player.coins -= paid
                    player.coins_spent_this_turn += paid
                    player.debt -= paid
                    context = {
                        "paid_debt": paid,
                        "remaining_debt": player.debt,
                        "remaining_coins": player.coins,
                    }
                    self.log_callback(
                        ("action", player.ai.name, f"pays {paid} Debt", context)
                    )
                    continue
                break

            if player.buys <= 0:
                break

            affordable = [c for c in self._get_affordable_cards(player) if c is not None]

            if not affordable:
                break

            choice = player.ai.choose_buy(self, affordable + [None])
            if choice is None:
                break

            # Update metrics for cards bought or purchased items
            if self.logger:
                self.logger.current_metrics.cards_bought[choice.name] = (
                    self.logger.current_metrics.cards_bought.get(choice.name, 0) + 1
                )

            cost = self.get_card_cost(player, choice)
            coins_spent = min(player.coins, cost)
            tokens_spent = max(0, cost - coins_spent)
            remaining_coins = player.coins - coins_spent
            remaining_tokens = player.coin_tokens - tokens_spent
            context = {
                "cost": cost,
                "remaining_coins": remaining_coins,
                "remaining_coin_tokens": remaining_tokens,
                "remaining_buys": player.buys - 1,
            }
            self.log_callback(("action", player.ai.name, f"buys {choice}", context))

            player.bought_this_turn.append(choice.name)
            player.buys -= 1
            player.coins_spent_this_turn += cost

            player.potions -= choice.cost.potions

            player.coins -= coins_spent
            player.coin_tokens -= tokens_spent


            if getattr(choice, "is_event", False):
                choice.on_buy(self, player)
            elif getattr(choice, "is_project", False):
                # Add a copy of the project to the player's owned projects
                player.projects.append(choice)
                choice.on_buy(self, player)
            else:
                self.supply[choice.name] -= 1
                self.log_callback(("supply_change", choice.name, -1, self.supply[choice.name]))
                choice.on_buy(self)
                gained_card = self.gain_card(player, choice)

                self._handle_on_buy_in_play_effects(player, choice, gained_card)

                if player.goons_played:
                    player.vp_tokens += player.goons_played

                if getattr(player, "merchant_guilds_played", 0) and not getattr(choice, "is_event", False):
                    player.coin_tokens += player.merchant_guilds_played

                self._trigger_haggler_bonus(player, choice)


            if choice.cost.debt:
                player.debt += choice.cost.debt

            if getattr(player, "charm_next_buy_copies", 0):
                copies_to_gain = min(
                    player.charm_next_buy_copies, self.supply.get(choice.name, 0)
                )
                for _ in range(copies_to_gain):
                    self.supply[choice.name] -= 1
                    self.gain_card(player, get_card(choice.name))
                player.charm_next_buy_copies = 0


        self._handle_buy_phase_end(player)
        self.phase = "cleanup"

    def _handle_buy_phase_end(self, player: PlayerState) -> None:
        """Resolve end-of-buy-phase triggers like Treasury and Joust."""
        for card in list(player.in_play):
            if hasattr(card, "on_buy_phase_end"):
                card.on_buy_phase_end(self)
            if hasattr(card, "on_cleanup_return_province"):
                card.on_cleanup_return_province(player)

    def get_card_cost(self, player: PlayerState, card: Card) -> int:
        """Return the coin cost of a card after modifiers."""
        cost = card.cost.coins

        if hasattr(card, "cost_modifier"):
            cost += card.cost_modifier(self, player)

        if getattr(player, "cost_reduction", 0):
            cost -= player.cost_reduction

        quarry_discount = sum(1 for c in player.in_play if c.name == "Quarry")
        if quarry_discount and card.is_action:
            cost -= 2 * quarry_discount

        return max(0, cost)

    def _get_affordable_cards(self, player):
        """Helper to get list of affordable cards, events and projects."""

        if player.debt > 0:
            return []

        affordable = []
        available_coins = player.coins + player.coin_tokens

        for card_name, count in self.supply.items():
            if count > 0:
                card = get_card(card_name)
                cost = self.get_card_cost(player, card)
                if (
                    cost <= available_coins
                    and card.cost.potions <= player.potions
                    and card.may_be_bought(self)
                    and card_name not in player.banned_buys
                    and (not player.cannot_buy_actions or not card.is_action)
                ):
                    affordable.append(card)

        for event in self.events:
            if (
                event.cost.coins <= available_coins
                and event.cost.potions <= player.potions
                and event.may_be_bought(self, player)
            ):
                affordable.append(event)

        for project in self.projects:
            if (
                project not in player.projects
                and project.cost.coins <= available_coins
                and project.cost.potions <= player.potions
                and project.may_be_bought(self, player)
            ):
                affordable.append(project)

        return affordable

    def _complete_purchase(self, player, card):
        """Helper to complete a card purchase."""
        cost = self.get_card_cost(player, card)
        coins_spent = min(player.coins, cost)
        tokens_spent = max(0, cost - coins_spent)
        player.buys -= 1
        player.coins_spent_this_turn += cost
        player.coins -= coins_spent
        player.coin_tokens -= tokens_spent
        player.potions -= card.cost.potions
        if card.cost.debt:
            player.debt += card.cost.debt
        self.supply[card.name] -= 1

        card.on_buy(self)
        self.gain_card(player, card)

        if player.goons_played:
            player.vp_tokens += player.goons_played

        if getattr(player, "merchant_guilds_played", 0):
            player.coin_tokens += player.merchant_guilds_played

        self._trigger_haggler_bonus(player, card)

    def handle_cleanup_phase(self):
        """Handle the cleanup phase of a turn."""
        player = self.current_player

        # Log turn summary before resetting state
        self.log_callback(
            (
                "turn_summary",
                player.ai.name,
                player.actions_this_turn,
                list(player.bought_this_turn),
                player.coins_spent_this_turn + player.coins,
            )
        )

        player.actions_this_turn = 0
        player.bought_this_turn = []

        # Discard hand and in-play cards
        scheme_count = sum(1 for card in player.in_play if card.name == "Scheme")
        if scheme_count:
            playable_actions = [card for card in player.in_play if card.is_action]
            for _ in range(scheme_count):
                if not playable_actions:
                    break
                chosen = max(
                    playable_actions,
                    key=lambda c: (c.cost.coins, c.stats.cards, c.stats.actions, c.name),
                )
                playable_actions.remove(chosen)
                if chosen in player.in_play:
                    player.in_play.remove(chosen)
                player.deck.insert(0, chosen)

        hand_cards = list(player.hand)
        player.hand = []
        self.discard_cards(player, hand_cards, from_cleanup=True)

        # Duration cards remain in play until their lingering effects finish.
        in_play_cards = list(player.in_play)
        player.in_play = []
        durations_to_keep = set(player.duration + player.multiplied_durations)

        trickster_selected: list[Card] = []
        trickster_uses = getattr(player, "trickster_uses_remaining", 0)
        if trickster_uses > 0:
            treasures_in_play = [card for card in in_play_cards if card.is_treasure]
            if treasures_in_play:
                max_set_aside = min(trickster_uses, len(treasures_in_play))
                chosen = player.ai.choose_treasures_to_set_aside_with_trickster(
                    self, player, list(treasures_in_play), max_set_aside
                )
                remaining_choices = list(treasures_in_play)
                for card in chosen:
                    if card in remaining_choices and card in in_play_cards:
                        remaining_choices.remove(card)
                        in_play_cards.remove(card)
                        trickster_selected.append(card)
                if trickster_selected:
                    player.trickster_set_aside.extend(trickster_selected)
                    player.trickster_uses_remaining = max(
                        0, player.trickster_uses_remaining - len(trickster_selected)
                    )

        for card in in_play_cards:
            if card in durations_to_keep:
                player.in_play.append(card)
            elif (
                card.name == "Walled Village"
                and getattr(player, "walled_villages_played", 0) <= 1
            ):
                player.deck.insert(0, card)
            else:
                if card.name == "Capital":
                    player.debt += 6
                    context = {
                        "gained_debt": 6,
                        "total_debt": player.debt,
                    }
                    self.log_callback(
                        ("action", player.ai.name, "gains 6 Debt from Capital", context)
                    )
                self.discard_card(player, card, from_cleanup=True)

        if player.trickster_set_aside:
            player.hand.extend(player.trickster_set_aside)
            player.trickster_set_aside = []
        player.trickster_uses_remaining = 0

        # Draw new hand
        player.draw_cards(5)

        # Reset resources
        player.actions = 1
        player.buys = 1
        player.coins = 0
        player.potions = 0
        player.ignore_action_bonuses = False
        player.collection_played = 0
        player.goons_played = 0
        player.groundskeeper_bonus = 0
        player.topdeck_gains = False
        player.cannot_buy_actions = False
        player.envious_effect_active = False
        player.cost_reduction = 0
        player.innovation_used = False
        player.cards_gained_this_turn = 0
        player.cards_gained_this_buy_phase = 0
        player.gained_victory_this_buy_phase = False
        player.flagship_pending = [
            card for card in player.flagship_pending if card in player.duration
        ]
        player.highwayman_blocked_this_turn = False
        player.insignia_active = False

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
        empty_piles = self.empty_piles
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
        """Draw cards for a player and log the result."""
        drawn = player.draw_cards(count)
        if drawn:
            context = {
                "drawn_cards": [c.name for c in drawn],
                "new_hand": [c.name for c in player.hand],
            }
            card_desc = "card" if len(drawn) == 1 else "cards"
            self.log_callback(
                (
                    "action",
                    player.ai.name,
                    f"draws {len(drawn)} {card_desc}",
                    context,
                )
            )
        return drawn

    def discard_card(self, player: PlayerState, card: Card, *, from_cleanup: bool = False) -> None:
        """Move ``card`` to the discard pile and handle discard reactions."""

        player.discard.append(card)
        if not from_cleanup:
            self._handle_discard_reactions(player, card)

    def discard_cards(
        self,
        player: PlayerState,
        cards: list[Card],
        *,
        from_cleanup: bool = False,
    ) -> None:
        """Discard each card in ``cards`` for ``player``."""

        for card in cards:
            self.discard_card(player, card, from_cleanup=from_cleanup)

    def _handle_discard_reactions(self, player: PlayerState, card: Card) -> None:
        """Resolve reactions that trigger when a card is discarded."""

        from ..cards.registry import get_card

        if card.name == "Tunnel" and self.supply.get("Gold", 0) > 0:
            self.supply["Gold"] -= 1
            self.gain_card(player, get_card("Gold"))
        elif card.name == "Weaver":
            if not player.ai.should_play_weaver_on_discard(self, player, card):
                return
            if card in player.discard:
                player.discard.remove(card)
            elif card in player.hand:
                player.hand.remove(card)
            else:
                return
            player.in_play.append(card)
            card.on_play(self)
        elif hasattr(card, "react_to_discard"):
            card.react_to_discard(self, player)

    def give_curse_to_player(self, player, *, to_hand: bool = False):
        """Give a curse card to a player.

        When ``to_hand`` is ``True`` the gained Curse is moved directly to the
        player's hand after resolving standard gain effects.
        """

        from ..cards.registry import get_card  # Import here to avoid circular dependency

        if self.supply.get("Curse", 0) <= 0:
            return False

        curse = get_card("Curse")
        self.supply["Curse"] -= 1
        gained = self.gain_card(player, curse)

        if to_hand and gained:
            if gained in player.discard:
                player.discard.remove(gained)
            elif gained in player.deck:
                player.deck.remove(gained)
            if gained not in player.hand:
                player.hand.append(gained)

        return True

    def _ensure_hex_deck(self) -> None:
        from dominion.hexes import create_hex_deck

        if not self.hex_deck:
            if self.hex_discard:
                self.hex_deck = list(self.hex_discard)
                random.shuffle(self.hex_deck)
                self.hex_discard = []
            else:
                self.hex_deck = create_hex_deck()

    def draw_hex(self) -> Optional[str]:
        """Draw the next Hex name from the Hex deck, shuffling if needed."""

        self._ensure_hex_deck()
        if not self.hex_deck:
            return None
        return self.hex_deck.pop()

    def resolve_hex(self, player: PlayerState, hex_name: str) -> None:
        """Apply the Hex ``hex_name`` to ``player`` and log the result."""

        if not hex_name:
            return

        from dominion.hexes import resolve_hex

        self.log_callback(("action", player.ai.name, f"receives Hex: {hex_name}", {}))
        resolve_hex(hex_name, self, player)

    def discard_hex(self, hex_name: Optional[str]) -> None:
        """Place a revealed Hex into the Hex discard pile."""

        if hex_name:
            self.hex_discard.append(hex_name)

    def give_hex_to_player(self, player):
        """Give the targeted player the next Hex from the Hex deck."""

        hex_name = self.draw_hex()
        if not hex_name:
            return None

        self.resolve_hex(player, hex_name)
        self.discard_hex(hex_name)
        return hex_name

    def gain_card(self, player: PlayerState, card: Card, to_deck: bool = False) -> Card:
        """Add a card to a player's discard or deck, honoring topdeck effects.

        If the player has a matching card on their Exile mat, that card is
        reclaimed instead of the newly gained copy.
        """

        reclaimed = None
        for idx, exiled in enumerate(player.exile):
            if exiled.name == card.name:
                reclaimed = player.exile.pop(idx)
                if exiled in player.invested_exile:
                    player.invested_exile.remove(exiled)
                break

        actual_card = reclaimed or card
        destination_is_deck = to_deck

        if not reclaimed:
            actual_card = self._handle_trader_exchange(
                player, card, actual_card, destination_is_deck
            )

        if not destination_is_deck and getattr(player, "topdeck_gains", False):
            destination_is_deck = True

        if (
            not destination_is_deck
            and getattr(player, "insignia_active", False)
            and player.ai.should_topdeck_with_insignia(self, player, actual_card)
        ):
            destination_is_deck = True

        if reclaimed and card.name in self.supply:
            # Caller already decremented the supply; restore it since the
            # Exiled card is being used instead.
            self.supply[card.name] = self.supply.get(card.name, 0) + 1

        if destination_is_deck:
            player.deck.insert(0, actual_card)
        else:
            player.discard.append(actual_card)
        actual_card.on_gain(self, player)

        self._handle_trade_route_token(actual_card)
        self._handle_watchtower_reaction(player, actual_card)
        self._handle_royal_seal_reaction(player, actual_card)

        for project in player.projects:
            if hasattr(project, "on_gain"):
                project.on_gain(self, player, actual_card)

        if getattr(player, "groundskeeper_bonus", 0) and actual_card.is_victory:
            player.vp_tokens += player.groundskeeper_bonus

        self._trigger_invest_draw(actual_card.name, player)
        self._handle_fools_gold_reactions(player, actual_card)
        self._track_action_gain(player, actual_card)
        self._handle_cargo_ship_gain(player, actual_card)
        self._handle_opponent_gain_hooks(player, actual_card)

        if (
            hasattr(player, "cards_gained_this_buy_phase")
            and player is self.current_player
            and self.phase == "buy"
        ):
            player.cards_gained_this_buy_phase += 1

        if actual_card.is_victory and player is self.current_player and self.phase == "buy":
            player.gained_victory_this_buy_phase = True

        if hasattr(player, "cards_gained_this_turn"):
            player.cards_gained_this_turn += 1

        return actual_card

    def _handle_trader_exchange(
        self,
        player: PlayerState,
        original_card: Card,
        actual_card: Card,
        to_deck: bool,
    ) -> Card:
        """Allow Trader reactions to replace a gain with a Silver."""

        if self.supply.get("Silver", 0) <= 0:
            return actual_card

        if not any(card.name == "Trader" for card in player.hand):
            return actual_card

        if not player.ai.should_reveal_trader(self, player, original_card, to_deck=to_deck):
            return actual_card

        if original_card.name in self.supply:
            self.supply[original_card.name] = self.supply.get(original_card.name, 0) + 1

        self.supply["Silver"] -= 1
        replacement = get_card("Silver")
        context = {
            "replaced": original_card.name,
            "destination": "deck" if to_deck else "discard",
        }
        self.log_callback(("action", player.ai.name, "reveals Trader", context))
        return replacement

    def _trigger_invest_draw(self, card_name: str, gainer: PlayerState) -> None:
        """Resolve Invest event reactions for other players."""

        for other in self.players:
            if other is gainer:
                continue
            matches = [card for card in other.invested_exile if card.name == card_name]
            for _ in matches:
                self.draw_cards(other, 2)

    def _handle_on_buy_in_play_effects(
        self, player: PlayerState, bought_card: Card, gained_card: Card
    ) -> None:
        """Resolve cards like Hoard and Talisman that watch purchases."""

        if not player.in_play:
            return

        from ..cards.registry import get_card

        hoard_count = sum(1 for card in player.in_play if card.name == "Hoard")
        if hoard_count and gained_card.is_victory:
            for _ in range(hoard_count):
                if self.supply.get("Gold", 0) <= 0:
                    break
                self.supply["Gold"] -= 1
                self.gain_card(player, get_card("Gold"))

        talisman_count = sum(1 for card in player.in_play if card.name == "Talisman")
        if talisman_count and not bought_card.is_victory and bought_card.cost.coins <= 4:
            for _ in range(talisman_count):
                if self.supply.get(bought_card.name, 0) <= 0:
                    break
                self.supply[bought_card.name] -= 1
                self.gain_card(player, get_card(bought_card.name))

    def _handle_trade_route_token(self, gained_card: Card) -> None:
        """Move Trade Route tokens from piles to the mat when cards are gained."""

        if not self.trade_route_tokens_on_piles:
            return

        if self.trade_route_tokens_on_piles.get(gained_card.name):
            self.trade_route_tokens_on_piles[gained_card.name] = False
            self.trade_route_mat_tokens += 1

    def _handle_watchtower_reaction(self, player: PlayerState, gained_card: Card) -> None:
        """Offer Watchtower reactions for gains."""

        watchtowers = [card for card in player.hand if card.name == "Watchtower"]
        if not watchtowers:
            return

        decision = player.ai.choose_watchtower_reaction(self, player, gained_card)
        if decision not in {"trash", "topdeck"}:
            return

        if not self._remove_gained_card_from_zones(player, gained_card):
            return

        if decision == "trash":
            self.trash_card(player, gained_card)
        else:
            player.deck.append(gained_card)

    def _handle_royal_seal_reaction(self, player: PlayerState, gained_card: Card) -> None:
        """Allow Royal Seal to topdeck newly gained cards."""

        if not any(card.name == "Royal Seal" for card in player.in_play):
            return

        if not player.ai.should_topdeck_with_royal_seal(self, player, gained_card):
            return

        if self._remove_gained_card_from_zones(player, gained_card):
            player.deck.append(gained_card)

    @staticmethod
    def _remove_gained_card_from_zones(player: PlayerState, card: Card) -> bool:
        """Remove ``card`` from hand, discard, or deck if present."""

        if card in player.discard:
            player.discard.remove(card)
            return True
        if card in player.deck:
            player.deck.remove(card)
            return True
        if card in player.hand:
            player.hand.remove(card)
            return True
        return False

    def notify_invest(self, card_name: str, investing_player: PlayerState) -> None:
        """Notify players that an Invest event occurred for ``card_name``."""

        self._trigger_invest_draw(card_name, investing_player)

    def _handle_fools_gold_reactions(self, gainer: PlayerState, gained_card: Card) -> None:
        """Handle Fool's Gold reactions when a Province is gained."""

        if gained_card.name != "Province":
            return

        from ..cards.registry import get_card

        for other in self.players:
            if other is gainer:
                continue

            while True:
                fools_golds = [card for card in other.hand if card.name == "Fool's Gold"]
                if not fools_golds:
                    break
                if self.supply.get("Gold", 0) <= 0:
                    return
                if not self._should_trash_fools_gold(other):
                    break

                card = fools_golds[0]
                other.hand.remove(card)
                self.trash_card(other, card)
                self.supply["Gold"] -= 1
                self.gain_card(other, get_card("Gold"), to_deck=True)

    def _should_trash_fools_gold(self, player: PlayerState) -> bool:
        """Simple heuristic to decide if a player should reveal Fool's Gold."""

        count_in_hand = sum(1 for card in player.hand if card.name == "Fool's Gold")
        if count_in_hand > 1:
            return True

        existing_gold = sum(1 for card in player.all_cards() if card.name == "Gold")
        return existing_gold < 2

    def _maybe_play_guard_dogs(self, player: PlayerState) -> None:
        guard_dogs = [card for card in list(player.hand) if card.name == "Guard Dog"]
        for card in guard_dogs:
            if card not in player.hand:
                continue
            if not player.ai.should_play_guard_dog(self, player, card):
                continue
            player.hand.remove(card)
            player.in_play.append(card)
            card.on_play(self)

    def _trigger_haggler_bonus(self, player: PlayerState, bought_card: Card) -> None:
        """Resolve Haggler gains after ``bought_card`` is purchased."""

        haggler_count = sum(1 for card in player.in_play if card.name == "Haggler")
        if haggler_count == 0:
            return

        from ..cards.registry import get_card

        for _ in range(haggler_count):
            options: list[Card] = []
            for name, count in self.supply.items():
                if count <= 0:
                    continue
                card = get_card(name)
                if card.cost.coins < bought_card.cost.coins and not card.is_victory:
                    options.append(card)

            if not options:
                break

            choice = player.ai.choose_buy(self, options + [None])
            if not choice:
                break

            if self.supply.get(choice.name, 0) <= 0:
                continue

            self.supply[choice.name] -= 1
            self.gain_card(player, choice)

    def _track_action_gain(self, player: PlayerState, card: Card) -> None:
        if not card.is_action:
            return

        player.actions_gained_this_turn += 1

        if (
            player.actions_gained_this_turn >= 3
            and not player.cauldron_triggered
            and any(card_in_play.name == "Cauldron" for card_in_play in player.in_play)
        ):
            for other in self.players:
                if other is player:
                    continue
                self.give_curse_to_player(other)
            player.cauldron_triggered = True

    def player_has_shield(self, player: PlayerState) -> bool:
        """Check if the player has a Shield card in hand."""
        return any(card.name == "Shield" for card in player.hand)

    def attack_player(self, target: PlayerState, attack_fn) -> None:
        """Apply an attack to a player unless blocked by reactions."""
        self._maybe_play_guard_dogs(target)
        if self._player_blocks_attack(target):
            return

        attack_fn(target)

    def _player_blocks_attack(self, player: PlayerState) -> bool:
        if self.player_has_shield(player):
            self.log_callback(("action", player.ai.name, "reveals Shield to block the attack", {}))
            return True

        if self._maybe_reveal_moat(player):
            return True

        return False

    def _maybe_reveal_moat(self, player: PlayerState) -> bool:
        moats = [card for card in player.hand if card.name == "Moat"]
        if not moats:
            return False

        if not player.ai.should_reveal_moat(self, player):
            return False

        self.log_callback(("action", player.ai.name, "reveals Moat to block the attack", {}))
        return True

    def trash_card(self, player: PlayerState, card: Card) -> None:
        """Move a card to the trash and trigger related effects."""
        self.trash.append(card)
        card.on_trash(self, player)

        # Resolve project triggers for trashing
        for project in player.projects:
            if hasattr(project, "on_trash"):
                project.on_trash(self, player, card)

    def _handle_cargo_ship_gain(self, player: PlayerState, gained_card: Card) -> None:
        """Check if a Cargo Ship in play wants to set aside the gained card."""
        for card in list(player.in_play):
            if hasattr(card, "on_cargo_ship_gain"):
                if card.on_cargo_ship_gain(self, player, gained_card):
                    break

    def _handle_opponent_gain_hooks(self, gainer: PlayerState, gained_card: Card) -> None:
        """Resolve project hooks that trigger when another player gains a card."""
        for player in self.players:
            if player is gainer:
                continue
            for project in player.projects:
                if hasattr(project, "on_opponent_gain"):
                    project.on_opponent_gain(self, player, gained_card)

    def _update_final_metrics(self):
        """Update final game metrics including victory points."""
        if not self.logger:
            return

        # Calculate and store final victory points for each player
        for player in self.players:
            vp = player.get_victory_points()
            self.logger.current_metrics.victory_points[player.ai.name] = vp

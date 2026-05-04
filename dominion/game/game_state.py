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
    allies: list = field(default_factory=list)
    landmarks: list = field(default_factory=list)
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
    # Nocturne: Boons deck (analogous to Hexes)
    boons_deck: list[str] = field(default_factory=list)
    boons_discard: list[str] = field(default_factory=list)
    # Druid sets aside three random Boons at the start of the game; the
    # active player may receive any one of them when playing Druid.
    druid_boons: list[str] = field(default_factory=list)
    wild_hunt_pile_tokens: int = 0
    farmers_market_pile_tokens: int = 0
    temple_pile_tokens: int = 0
    tireless_piles: set = field(default_factory=set)  # card names with Tireless trait
    embargo_tokens: dict[str, int] = field(default_factory=dict)
    # Empires Tax: pile_name -> debt tokens currently on the pile.
    tax_tokens: dict[str, int] = field(default_factory=dict)

    # Dark Ages: ordered piles where the top card matters (Ruins, Knights).
    # ``pile_order[name]`` is a list of card-name strings; the top of the pile
    # is the LAST element. Pulling from these piles always pops the top.
    pile_order: dict[str, list[str]] = field(default_factory=dict)
    # Plunder Traits: per-game one trait modifies one Kingdom pile.
    trait_piles: dict = field(default_factory=dict)  # trait_name -> pile_name
    pile_traits: dict = field(default_factory=dict)  # pile_name -> trait_name
    hasty_set_aside: dict = field(default_factory=dict)  # PlayerState id -> list[Card]
    patient_mat: dict = field(default_factory=dict)  # PlayerState id -> list[Card]
    # Plunder card / event state hooks
    landing_party_pending: dict = field(default_factory=dict)
    quartermaster_mats: dict = field(default_factory=dict)
    enlarge_pending: dict = field(default_factory=dict)
    rush_pending: dict = field(default_factory=dict)
    mirror_pending: dict = field(default_factory=dict)

    # Rising Sun: Prophecies and Sun tokens
    prophecy: object = None
    sun_tokens: int = 0
    riverboat_set_aside: object = None  # Card set aside at game start for Riverboat
    harsh_winter_debt: dict = field(default_factory=dict)  # pile_name → debt tokens
    # Names of the Kingdom card piles (and their split-pile partners) used at
    # game setup. Tracked separately from the supply because Divine Wind
    # needs to remove only those piles, not non-Kingdom support piles like
    # Ruins, Spoils, or Horse.
    original_kingdom_pile_names: set = field(default_factory=set)

    # Cornucopia: Young Witch designates an extra $2/$3 Kingdom pile as the
    # Bane. A card from that pile, revealed from hand, blocks a Young Witch
    # attack against the holder.
    bane_card_name: str = ""

    # Renaissance: Artifacts. Populated by ``initialize_game`` when the
    # corresponding Kingdom card is in the supply.
    artifacts: dict = field(default_factory=dict)

    # Renaissance Fleet project: the set of players who own Fleet at game
    # end. They (and only they) take an extra round of turns.
    fleet_extra_round_active: bool = False
    fleet_extra_players: list = field(default_factory=list)

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

    def fire_prophecy_action_hooks(self, player: PlayerState, card: Card) -> None:
        """Fire the active Prophecy's after-Action-play hooks for ``card``.

        Used by Continue / Riverboat / Practice and any other code path that
        plays an Action card outside ``handle_action_phase``. The hooks are
        the same ones the action phase loop fires after each Action play
        (Great Leader's +1 Action, Approaching Army's +$1 from Attacks).
        """
        if self.prophecy is None or not self.prophecy.is_active:
            return
        self.prophecy.on_play_action(self, player, card)
        if card.is_attack:
            self.prophecy.on_play_attack(self, player, card)

    def remove_sun_token(self, count: int = 1) -> None:
        """Omen +1 Sun: remove ``count`` Sun tokens from the active Prophecy.

        When the last token is removed, the Prophecy activates and its rule
        text becomes effective for the rest of the game. No-ops when there is
        no active Prophecy or when tokens have already been depleted.
        """
        if self.prophecy is None:
            return
        if self.sun_tokens <= 0:
            return
        for _ in range(count):
            if self.sun_tokens <= 0:
                break
            self.sun_tokens -= 1
            if self.sun_tokens == 0 and not self.prophecy.is_active:
                self.prophecy.activate(self)
                break

    def initialize_game(
        self,
        ais: list,
        kingdom_cards: list[Card],
        use_shelters: bool = False,
        events: list = None,
        projects: list = None,
        ways: list = None,
        allies: list = None,
        prophecy: object = None,
        riverboat_set_aside: Card = None,
        landmarks: list = None,
    ):
        """Set up the game with given AIs and kingdom cards."""
        # Create PlayerState objects for each AI
        self.players = [PlayerState(ai) for ai in ais]
        # Snapshot the Kingdom selection before setup_supply expands the pile
        # set with split-pile partners. We extend the snapshot with the
        # partner names below since Divine Wind treats a split pile as one
        # Kingdom pile to remove.
        self.original_kingdom_pile_names = {c.name for c in kingdom_cards}
        for c in kingdom_cards:
            if isinstance(c, SplitPileMixin):
                self.original_kingdom_pile_names.add(c.partner_card_name)
            from dominion.cards.allies.wizards import (
                WIZARDS_PILE_ORDER,
                WizardsSplitCard,
            )
            if isinstance(c, WizardsSplitCard):
                self.original_kingdom_pile_names.update(WIZARDS_PILE_ORDER)
            from dominion.cards.allies._split_base import AlliesSplitCard
            if isinstance(c, AlliesSplitCard):
                self.original_kingdom_pile_names.update(c.pile_order)
        self.setup_supply(kingdom_cards)
        self.events = events or []
        self.projects = projects or []
        self.ways = ways or []
        self.allies = allies or []
        self.landmarks = landmarks or []
        for landmark in self.landmarks:
            landmark.setup(self)

        # Rising Sun: a Prophecy is dealt out whenever any Omen card is in the
        # supply. Sun tokens are placed based on player count.
        has_omen = any(card.is_omen for card in kingdom_cards)
        if prophecy is None and has_omen:
            from dominion.prophecies.registry import PROPHECY_TYPES
            if PROPHECY_TYPES:
                prophecy_class = random.choice(list(PROPHECY_TYPES.values()))
                prophecy = prophecy_class()
        if prophecy is not None:
            self.prophecy = prophecy
            tokens_per_count = {2: 5, 3: 8, 4: 10, 5: 12, 6: 13}
            self.sun_tokens = tokens_per_count.get(len(self.players), 5)
            prophecy.setup(self)
            self.log_callback(
                f"Prophecy: {prophecy.name} ({self.sun_tokens} Sun tokens)"
            )

        # Riverboat: a non-Duration Action card costing exactly $5 is set aside
        # at the start of the game and played at the start of the turn after
        # Riverboat is played.
        if riverboat_set_aside is not None:
            self.riverboat_set_aside = riverboat_set_aside
        elif any(c.name == "Riverboat" for c in kingdom_cards):
            self.riverboat_set_aside = self._pick_riverboat_set_aside(kingdom_cards)

        # Nocturne: collect heirlooms from kingdom cards (one Copper per
        # heirloom is swapped at player init).
        heirlooms = [
            getattr(c, "heirloom", None) for c in kingdom_cards
            if getattr(c, "heirloom", None)
        ]

        # Initialize players
        for player in self.players:
            player.initialize(use_shelters, heirlooms=heirlooms)

        # Nocturne: setup Boons-related infrastructure when needed.
        needs_boons = any(
            getattr(c, "uses_boons", False) for c in kingdom_cards
        )
        if needs_boons:
            from dominion.boons import create_boons_deck
            self.boons_deck = create_boons_deck()
            self.boons_discard = []
        # Druid sets aside three Boons regardless of which Boons are persistent.
        if any(c.name == "Druid" for c in kingdom_cards):
            self.setup_druid_boons()
        # Nocturne: extra non-supply piles needed by various cards
        self._setup_nocturne_extras(kingdom_cards)

        if self.baker_in_supply:
            for player in self.players:
                player.coin_tokens += 1

        # Empires Tax setup: when Tax is among the events, place 1 debt token
        # on each Supply pile at game start.
        if any(getattr(ev, "name", None) == "Tax" for ev in (self.events or [])):
            for pile_name in self.supply:
                self.tax_tokens[pile_name] = self.tax_tokens.get(pile_name, 0) + 1

        # Renaissance: create the relevant Artifacts when their anchoring
        # Kingdom cards are present. Artifacts start unheld and pass to
        # the active player when an anchor card is played.
        from dominion.artifacts import get_artifact
        artifact_triggers = {
            "Flag Bearer": ["Flag"],
            "Border Guard": ["Horn", "Lantern"],
            "Treasurer": ["Key"],
            "Swashbuckler": ["Treasure Chest"],
        }
        kingdom_names = {c.name for c in kingdom_cards}
        for trigger, names in artifact_triggers.items():
            if trigger in kingdom_names:
                for art_name in names:
                    if art_name not in self.artifacts:
                        self.artifacts[art_name] = get_artifact(art_name)
        # Allies rules: if any Liaison is in the kingdom and the caller did
        # not already specify an Ally, choose a random one. Without an Ally,
        # Liaison cards still grant Favors but those Favors have nothing
        # to spend on.
        if not self.allies and any(c.is_liaison for c in kingdom_cards):
            from dominion.allies.registry import ALLY_TYPES
            if ALLY_TYPES:
                ally_class = random.choice(list(ALLY_TYPES.values()))
                self.allies = [ally_class()]
                self.log_callback(f"Ally: {self.allies[0].name}")

        # Allies rules: when an Ally is in the game, each player starts with
        # 1 Favor. Without this, Ally abilities can't be activated until a
        # Liaison resolves, which skews early-turn behavior on Ally boards.
        if self.allies:
            for player in self.players:
                player.favors += 1

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

    def _pick_riverboat_set_aside(self, kingdom_cards: list[Card]) -> "Card | None":
        """Choose a non-Duration Action card costing exactly $5 not in the supply.

        Used at game setup when Riverboat is in the kingdom and the caller
        didn't pass an explicit set-aside card.
        """
        in_kingdom = {c.name for c in kingdom_cards}
        for name in get_all_card_names():
            if name in in_kingdom:
                continue
            try:
                card = get_card(name)
            except ValueError:
                continue
            if not card.is_action:
                continue
            if card.is_duration:
                continue
            if getattr(card, "is_event", False) or getattr(card, "is_project", False):
                continue
            if card.cost.coins != 5 or card.cost.debt != 0 or card.cost.potions != 0:
                continue
            return card
        return None

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

            # Wizards split pile: add the other three partners with
            # player-count-aware supply via each partner's starting_supply.
            from dominion.cards.allies.wizards import (
                WIZARDS_PILE_ORDER,
                WizardsSplitCard,
            )
            if isinstance(card, WizardsSplitCard):
                for partner_name in WIZARDS_PILE_ORDER:
                    if partner_name == card.name:
                        continue
                    if partner_name not in self.supply:
                        partner = get_card(partner_name)
                        self.supply[partner_name] = partner.starting_supply(self)

            # Allies four-card split piles (Augurs, Clashes, Forts,
            # Odysseys, Townsfolk).
            from dominion.cards.allies._split_base import AlliesSplitCard
            if isinstance(card, AlliesSplitCard):
                for partner_name in card.pile_order:
                    if partner_name == card.name:
                        continue
                    if partner_name not in self.supply:
                        partner = get_card(partner_name)
                        self.supply[partner_name] = partner.starting_supply(self)

            extras = card.get_additional_piles()
            for name, count in extras.items():
                if name not in self.supply:
                    self.supply[name] = count

            if card.name == "Baker":
                self.baker_in_supply = True

        # Empires Castles: any Castle in the kingdom expands the pile to all
        # 8 distinct Castle cards, each with player-count-aware supply.
        from dominion.cards.empires.castles import CASTLE_ORDER
        if any(c.name in CASTLE_ORDER for c in kingdom_cards):
            for name in CASTLE_ORDER:
                castle = get_card(name)
                self.supply[name] = castle.starting_supply(self)
                self.original_kingdom_pile_names.add(name)

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

        # Cornucopia: Young Witch designates a Bane Kingdom pile costing $2 or
        # $3. If one of the already-chosen Kingdom cards qualifies, use it;
        # otherwise add an extra $2/$3 pile to the Supply.
        if any(card.name == "Young Witch" for card in kingdom_cards):
            self._setup_young_witch_bane(kingdom_cards)

        self._setup_dark_ages_piles(kingdom_cards)

    def _setup_young_witch_bane(self, kingdom_cards: list[Card]) -> None:
        """Designate the Bane card pile required by Young Witch."""

        BASIC_NAMES = {
            "Copper", "Silver", "Gold", "Platinum",
            "Estate", "Duchy", "Province", "Colony", "Curse",
        }

        in_kingdom = [
            c for c in kingdom_cards
            if c.cost.coins in (2, 3)
            and c.cost.potions == 0
            and c.cost.debt == 0
            and c.name != "Young Witch"
            and not getattr(c, "is_event", False)
            and not getattr(c, "is_project", False)
        ]
        if in_kingdom:
            chosen = min(in_kingdom, key=lambda c: (c.cost.coins, c.name))
            self.bane_card_name = chosen.name
            self.original_kingdom_pile_names.add(chosen.name)
            return

        kingdom_names = {c.name for c in kingdom_cards}
        candidate_name: str | None = None
        candidate_card: Card | None = None
        for name in get_all_card_names():
            if name in kingdom_names or name in BASIC_NAMES:
                continue
            if name in self.supply:
                continue
            try:
                card = get_card(name)
            except ValueError:
                continue
            if card.cost.coins not in (2, 3):
                continue
            if card.cost.potions != 0 or card.cost.debt != 0:
                continue
            if getattr(card, "is_event", False) or getattr(card, "is_project", False):
                continue
            if not card.may_be_bought(self):
                continue
            candidate_name = name
            candidate_card = card
            break

        if candidate_name and candidate_card is not None:
            self.supply[candidate_name] = candidate_card.starting_supply(self)
            self.bane_card_name = candidate_name
            self.original_kingdom_pile_names.add(candidate_name)

    def _setup_dark_ages_piles(self, kingdom_cards: list[Card]) -> None:
        """Build the shuffled Ruins / Knights piles and Madman / Mercenary piles."""
        from dominion.cards.dark_ages.ruins import RUIN_VARIANT_NAMES
        from dominion.cards.dark_ages.knights import KNIGHT_NAMES

        if "Ruins" in self.supply:
            n_players = max(2, len(self.players))
            ruins_count = 10 * (n_players - 1)
            ruin_pool: list[str] = []
            per_variant = (ruins_count // len(RUIN_VARIANT_NAMES)) + 1
            for variant in RUIN_VARIANT_NAMES:
                ruin_pool.extend([variant] * per_variant)
            random.shuffle(ruin_pool)
            ruin_pool = ruin_pool[:ruins_count]
            random.shuffle(ruin_pool)
            self.pile_order["Ruins"] = ruin_pool
            self.supply["Ruins"] = len(ruin_pool)

        if "Knights" in self.supply:
            order = list(KNIGHT_NAMES)
            random.shuffle(order)
            self.pile_order["Knights"] = order
            self.supply["Knights"] = len(order)

        if any(card.name == "Hermit" for card in kingdom_cards):
            self.supply["Madman"] = 10

        if any(card.name == "Urchin" for card in kingdom_cards):
            self.supply["Mercenary"] = 10

    def gain_ruins(self, target) -> "Card | None":
        """Resolve a "gain a Ruins" by handing over the top of the Ruins pile."""
        order = self.pile_order.get("Ruins")
        if not order:
            if self.supply.get("Ruins", 0) > 0:
                self.supply["Ruins"] -= 1
                return self.gain_card(target, get_card("Ruins"))
            return None

        if not order:
            return None
        top_name = order.pop()
        self.supply["Ruins"] = max(0, self.supply.get("Ruins", 0) - 1)
        return self.gain_card(target, get_card(top_name))

    def top_of_pile(self, pile_name: str) -> "Card | None":
        """Return a card object representing the top of an ordered pile, or None."""
        order = self.pile_order.get(pile_name)
        if not order:
            return None
        return get_card(order[-1])

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
        """Return number of empty supply piles, counting split/Wizards piles once."""
        from dominion.cards.allies.wizards import WIZARDS_PILE_ORDER, WizardsSplitCard
        from dominion.cards.allies._split_base import AlliesSplitCard

        counted: set[str] = set()
        empties = 0
        for name in list(self.supply.keys()):
            if name in counted:
                continue
            card = get_card(name)
            if isinstance(card, WizardsSplitCard):
                wizard_names = set(WIZARDS_PILE_ORDER)
                counted.update(wizard_names)
                if all(self.supply.get(n, 0) == 0 for n in wizard_names if n in self.supply):
                    empties += 1
            elif isinstance(card, AlliesSplitCard):
                pile_names = set(card.pile_order)
                counted.update(pile_names)
                if all(self.supply.get(n, 0) == 0 for n in pile_names if n in self.supply):
                    empties += 1
            elif isinstance(card, SplitPileMixin):
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
        player.gained_victory_this_turn = False
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
        player.harbor_village_pending = 0
        player.continue_used_this_turn = False
        # Menagerie state resets
        player.cavalry_returned_this_turn = False
        player.kiln_pending = 0
        # Daimyo's "next non-Command Action this turn" replay expires when the
        # turn ends without a triggering Action being played.
        player.daimyo_pending = 0
        # Merchant's "first Silver this turn = +$1" tracking
        player.merchant_silver_bonus = 0
        player.merchant_silver_bonus_used = False
        # Prosperity 2E: Tiara's once-per-turn replay resets each turn
        player.tiara_replay_used = False
        # Prosperity 2E: War Chest names tracked per turn
        player.war_chest_named_this_turn = []
        # Coppersmith bonus is per-turn.
        player.coppersmiths_played = 0
        # Enchantress: re-arm the "first Action this turn" override flag if a
        # caster's Enchantress is still active over this opponent.
        player.enchantress_used_this_turn = False
        # Renaissance Priest's rest-of-turn trigger resets each turn.
        player.priest_played_this_turn = 0

        # Nocturne — reset per-turn counter
        player.cards_gained_this_turn_count = 0

        # Nocturne — persistent Boons given last turn fire their start-of-turn bonus.
        active_boons = list(getattr(player, "active_boons", []))
        player.active_boons = []
        for boon in active_boons:
            if boon == "The Field's Gift":
                if not player.ignore_action_bonuses:
                    player.actions += 1
                player.coins += 1
            elif boon == "The Forest's Gift":
                player.buys += 1
                player.coins += 1
            self.discard_boon(boon)

        # Nocturne — Lost in the Woods (Fool): receive a Boon
        if getattr(player, "lost_in_the_woods", False):
            self.receive_boon(player)

        # Nocturne — Blessed Village pending Boons
        for _ in range(getattr(player, "pending_blessed_boons", 0)):
            self.receive_boon(player)
        player.pending_blessed_boons = 0

        # Nocturne — Ghost: play the set-aside Action twice over two turns
        if getattr(player, "ghost_pending_actions", None):
            updated: list = []
            for entry in player.ghost_pending_actions:
                action_card, plays_left = entry
                if plays_left <= 0:
                    continue
                if action_card not in player.in_play:
                    player.in_play.append(action_card)
                self.log_callback(
                    ("action", player.ai.name, f"Ghost replays {action_card}", {})
                )
                action_card.on_play(self)
                plays_left -= 1
                if plays_left > 0:
                    updated.append((action_card, plays_left))
            player.ghost_pending_actions = updated

        # Return any cards delayed by the Delay event
        if self.current_player.delayed_cards:
            self.current_player.hand.extend(self.current_player.delayed_cards)
            self.current_player.delayed_cards = []

        # Menagerie Reap event: play any set-aside Golds from previous turn.
        reap_set_aside = getattr(self.current_player, "reap_set_aside", None)
        if reap_set_aside:
            self.current_player.reap_set_aside = []
            for gold_card in reap_set_aside:
                self.current_player.in_play.append(gold_card)
                gold_card.on_play(self)

        # Menagerie Way of the Squirrel: +2 Cards next turn (banked draw).
        squirrel_pending = getattr(self.current_player, "squirrel_pending", 0)
        if squirrel_pending > 0:
            self.draw_cards(self.current_player, squirrel_pending)
            self.current_player.squirrel_pending = 0

        # Menagerie Way of the Turtle: play set-aside cards now.
        turtle_set_aside = getattr(self.current_player, "turtle_set_aside", None)
        if turtle_set_aside:
            self.current_player.turtle_set_aside = []
            for c in turtle_set_aside:
                self.current_player.in_play.append(c)
                c.on_play(self)

        # Resolve project effects that occur at the start of the turn
        for project in self.current_player.projects:
            project.on_turn_start(self, self.current_player)

        # Renaissance: Artifact start-of-turn effects for the holder
        for artifact in self.artifacts.values():
            if artifact.holder is self.current_player:
                artifact.on_holder_turn_start(self, self.current_player)

        # Resolve Ally effects (e.g. Cave Dwellers' Favor-spending hook)
        for ally in self.allies:
            ally.on_turn_start(self, self.current_player)

        # Rising Sun: Prophecy start-of-turn hook (Kind Emperor)
        if self.prophecy is not None and self.prophecy.is_active:
            self.prophecy.on_turn_start(self, self.current_player)

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

        # Plunder per-turn flag resets.
        self.current_player.cards_trashed_this_turn = 0
        self.current_player.mining_road_triggered = False
        self.current_player.search_triggered = False

        # Plunder Shy trait: discard Shy-pile cards in hand for +2 Cards.
        self._handle_shy_start_of_turn(self.current_player)

        # Plunder Hasty trait: play any Hasty cards set aside.
        self._handle_hasty_start_of_turn(self.current_player)

        # Plunder Patient trait: play any cards on the Patient mat.
        self._handle_patient_start_of_turn(self.current_player)

        # Plunder Quartermaster: gain a card or take all from mat.
        self._handle_quartermaster_start_of_turn(self.current_player)

        self.phase = "action"

    def _handle_shy_start_of_turn(self, player: PlayerState) -> None:
        shy_pile = self.trait_piles.get("Shy")
        if not shy_pile:
            return
        shy_cards = [c for c in player.hand if c.name == shy_pile]
        for card in shy_cards:
            should_use = True
            if hasattr(player.ai, "should_use_shy"):
                should_use = player.ai.should_use_shy(self, player, card)
            if should_use:
                player.hand.remove(card)
                self.discard_card(player, card)
                self.draw_cards(player, 2)

    def _handle_hasty_start_of_turn(self, player: PlayerState) -> None:
        cards = self.hasty_set_aside.pop(id(player), [])
        for card in cards:
            if card.is_action:
                player.in_play.append(card)
                player.actions_this_turn += 1
                card.on_play(self)
            elif card.is_treasure:
                player.in_play.append(card)
                card.on_play(self)
            else:
                player.discard.append(card)

    def _handle_patient_start_of_turn(self, player: PlayerState) -> None:
        cards = self.patient_mat.pop(id(player), [])
        for card in cards:
            if card.is_action:
                player.in_play.append(card)
                player.actions_this_turn += 1
                card.on_play(self)
            elif card.is_treasure:
                player.in_play.append(card)
                card.on_play(self)
            else:
                player.discard.append(card)

    def _handle_quartermaster_start_of_turn(self, player: PlayerState) -> None:
        from ..cards.registry import get_card

        quartermasters = [c for c in player.duration if c.name == "Quartermaster"]
        if not quartermasters:
            return
        for _qm in quartermasters:
            mat = self.quartermaster_mats.setdefault(id(player), [])
            take_all = False
            if mat and hasattr(player.ai, "quartermaster_take_all"):
                take_all = player.ai.quartermaster_take_all(self, player, list(mat))
            elif mat:
                take_all = len(mat) >= 2
            if take_all:
                player.hand.extend(mat)
                self.quartermaster_mats[id(player)] = []
            else:
                candidates = []
                for name, count in self.supply.items():
                    if count <= 0:
                        continue
                    try:
                        card = get_card(name)
                    except ValueError:
                        continue
                    if (
                        card.cost.coins <= 4
                        and card.cost.potions == 0
                        and card.cost.debt == 0
                    ):
                        candidates.append(card)
                if not candidates:
                    continue
                candidates.sort(key=lambda c: (c.cost.coins, c.name), reverse=True)
                non_v = [c for c in candidates if not c.is_victory]
                pick = (non_v or candidates)[0]
                if self.supply.get(pick.name, 0) > 0:
                    self.supply[pick.name] -= 1
                    self.quartermaster_mats[id(player)].append(pick)

    def do_duration_phase(self):
        """Handle effects of duration cards from previous turn."""
        player = self.current_player

        # Process duration cards that were played last turn
        for card in player.duration[:]:
            # Log duration card effect
            coins_before = player.coins
            actions_before = player.actions
            card.on_duration(self)
            coins_after = player.coins
            actions_after = player.actions
            context = {
                "coins_before": coins_before,
                "coins_after": coins_after,
                "actions_before": actions_before,
                "actions_after": actions_after,
            }
            self.log_callback(("action", player.ai.name,
                f"resolves duration effect of {card} "
                f"(+{coins_after - coins_before} coins, +{actions_after - actions_before} actions; "
                f"now {coins_after} coins, {actions_after} actions)",
                context))

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
        enlightened = (
            self.prophecy is not None
            and self.prophecy.is_active
            and self.prophecy.name == "Enlightenment"
        )

        while True:
            action_cards = [card for card in player.hand if card.is_action]
            # Rising Sun: Enlightenment turns Treasures into Actions for all
            # purposes — they can be played from your hand in the Action phase.
            if enlightened:
                action_cards += [
                    card for card in player.hand
                    if card.is_treasure and not card.is_action
                ]
            # Rising Sun: Shadow cards may be played from the deck whenever
            # you could normally play an Action.
            shadow_in_deck = [card for card in player.deck if card.is_shadow]
            playable = action_cards + shadow_in_deck

            if not playable:
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

            choice = player.ai.choose_action(self, playable + [None])
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
            # Shadow cards are played from the deck; everything else from hand.
            if choice in player.hand:
                player.hand.remove(choice)
            elif choice in player.deck:
                player.deck.remove(choice)
            player.in_play.append(choice)
            # Track coins before play for Harbor Village bonus
            coins_before_action = player.coins
            harbor_pending = getattr(player, "harbor_village_pending", 0)

            # Training token: +$1 when playing a card from the trained pile
            training_pile = getattr(player, "training_pile", None)

            if way:
                way.apply(self, choice)
                if training_pile and choice.name == training_pile:
                    player.coins += 1
                # Menagerie: Kiln triggers on Way-played card too.
                self._maybe_kiln_gain(player, choice)
            else:
                flagships_to_resolve: list[Card] = []
                pending_flagships = getattr(player, "flagship_pending", [])
                if pending_flagships and not getattr(choice, "is_command", False):
                    flagships_to_resolve = list(pending_flagships)
                    pending_flagships.clear()
                    for flagship in flagships_to_resolve:
                        if flagship in player.duration:
                            player.duration.remove(flagship)

                # Rising Sun: Daimyo replays the next non-Command Action.
                # Multiple Daimyos stack and all replay the same card.
                daimyo_replays = 0
                if not getattr(choice, "is_command", False):
                    daimyo_replays = getattr(player, "daimyo_pending", 0)
                    player.daimyo_pending = 0

                # Plunder Reckless trait: cards from the Reckless pile play twice.
                reckless_extra = 1 if self.pile_traits.get(choice.name) == "Reckless" else 0

                # Plunder Rush event: next Action plays twice.
                rush_extra = 0
                rush_count = self.rush_pending.get(id(player), 0)
                if rush_count > 0:
                    rush_extra = 1
                    self.rush_pending[id(player)] = rush_count - 1

                plays = 1 + len(flagships_to_resolve) + daimyo_replays + reckless_extra + rush_extra
                for _ in range(plays):
                    if enlightened and choice.is_treasure and not choice.is_action:
                        # Treasure played in Action phase under Enlightenment:
                        # +1 Card, +1 Action (instead of its normal text).
                        self.draw_cards(player, 1)
                        player.actions += 1
                    elif (
                        choice.is_action
                        and getattr(player, "enchantress_active", False)
                        and not getattr(player, "enchantress_used_this_turn", False)
                    ):
                        # Empires Enchantress: opponent's first Action this
                        # turn under Enchantress's duration is replaced with
                        # "+1 Card, +1 Action".
                        player.enchantress_used_this_turn = True
                        player.enchantress_active = False
                        self.draw_cards(player, 1)
                        player.actions += 1
                        self.log_callback(
                            (
                                "action",
                                player.ai.name,
                                f"is enchanted while playing {choice} (gets +1 Card +1 Action instead)",
                                {},
                            )
                        )
                    else:
                        choice.on_play(self)
                    if training_pile and choice.name == training_pile:
                        player.coins += 1

                    # Menagerie: Kiln — next card played, gain a copy of it.
                    self._maybe_kiln_gain(player, choice)

                    # Rising Sun: Prophecy hooks fire after each play
                    if self.prophecy is not None and self.prophecy.is_active:
                        self.prophecy.on_play_action(self, player, choice)
                        if choice.is_attack:
                            self.prophecy.on_play_attack(self, player, choice)

                    # Dark Ages: Urchin reacts to a freshly played Attack.
                    if choice.is_attack and choice.name != "Urchin":
                        for urchin in [
                            c for c in list(player.in_play)
                            if c.name == "Urchin" and c is not choice
                        ]:
                            try:
                                urchin.react_to_attack_played(self, player, choice)
                            except AttributeError:
                                pass
                    # Allies hook: any Ally that reacts to plays
                    # (Circle of Witches, League of Shopkeepers,
                    # Fellowship of Scribes).
                    for ally in self.allies:
                        on_play = getattr(ally, "on_play_card", None)
                        if on_play is not None:
                            on_play(self, player, choice)

            # Harbor Village bonus: +$1 if the action gave +$
            if harbor_pending > 0 and choice.name != "Harbor Village":
                coins_gained = player.coins - coins_before_action
                if coins_gained > 0:
                    player.coins += 1
                player.harbor_village_pending = max(0, harbor_pending - 1)

            # Plunder Inspiring trait: after playing, may play an Action you
            # don't already have a copy of in play.
            self._maybe_inspiring_extra_play(player, choice)

        self.phase = "treasure"

    def _maybe_inspiring_extra_play(self, player: PlayerState, just_played: Card) -> None:
        if self.pile_traits.get(just_played.name) != "Inspiring":
            return
        in_play_names = {c.name for c in player.in_play}
        candidates = [
            c for c in player.hand
            if c.is_action and c.name not in in_play_names
        ]
        if not candidates:
            return
        choice = player.ai.choose_action(self, candidates + [None])
        if choice is None:
            return
        player.hand.remove(choice)
        player.in_play.append(choice)
        player.actions_this_turn += 1
        choice.on_play(self)

    def _handle_start_of_buy_phase_effects(self) -> None:
        """Apply state effects that trigger at the start of the buy phase."""

        player = self.current_player
        player.cannot_buy_actions = False
        player.envious_effect_active = False
        player.cards_gained_this_buy_phase = 0
        player.gained_victory_this_buy_phase = False

        # Renaissance: Artifact start-of-buy-phase effects (Treasure Chest)
        for artifact in self.artifacts.values():
            if artifact.holder is player:
                artifact.on_holder_buy_phase_start(self, player)

        # Renaissance: project end-of-buy-phase markers reset for Pageant /
        # Exploration tracking.
        player.gained_action_or_treasure_this_buy_phase = False

        if player.deluded:
            player.deluded = False
            player.cannot_buy_actions = True

        if player.envious:
            player.envious = False
            player.envious_effect_active = True

        # Empires Landmarks: Arena's start-of-buy discard-for-VP option.
        for landmark in self.landmarks:
            landmark.on_buy_phase_start(self, player)

        # Rising Sun Flourishing Trade: leftover Action plays become Buys.
        if (
            self.prophecy is not None
            and self.prophecy.is_active
            and self.prophecy.name == "Flourishing Trade"
            and player.actions > 0
        ):
            converted = player.actions
            player.actions = 0
            player.buys += converted

        # Allies: hook called at start of buy phase
        # (Market Towns, Peaceful Cult).
        for ally in self.allies:
            hook = getattr(ally, "on_buy_phase_start", None)
            if hook is not None:
                hook(self, player)

    def handle_treasure_phase(self):
        """Handle the treasure phase of a turn."""
        player = self.current_player

        self._handle_start_of_buy_phase_effects()

        capitalism = any(
            getattr(p, "name", "") == "Capitalism" for p in player.projects
        )

        while True:
            treasures = [card for card in player.hand if card.is_treasure]
            if capitalism:
                treasures += [
                    card
                    for card in player.hand
                    if card.is_action
                    and not card.is_treasure
                    and card.stats.coins > 0
                ]
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
                # Corsair trashes AFTER on_play: the treasure is fully played
                # (so its +$ applies and any "while in play" counters tick),
                # then Corsair removes it from in-play to the trash.
                choice.on_play(self)
                # Plunder Reckless trait: Treasures from Reckless pile play twice.
                if self.pile_traits.get(choice.name) == "Reckless":
                    if choice in player.in_play:
                        choice.on_play(self)
                self._maybe_corsair_trash(player, choice)
                # Menagerie: Kiln — gain a copy of the next card played.
                self._maybe_kiln_gain(player, choice)
                coins_after = player.coins
                if (
                    player.envious_effect_active
                    and choice.name in {"Silver", "Gold"}
                    and coins_after > coins_before + 1
                ):
                    player.coins = coins_before + 1
                    coins_after = player.coins

                # Rising Sun: Prophecy hooks fire after each treasure plays
                if self.prophecy is not None and self.prophecy.is_active:
                    self.prophecy.on_play_treasure(self, player, choice)

                # Allies hook: City-state, League of Shopkeepers,
                # Fellowship of Scribes can react to treasures played.
                for ally in self.allies:
                    on_play = getattr(ally, "on_play_card", None)
                    if on_play is not None:
                        on_play(self, player, choice)

                # Prosperity 2E: Tiara — once per turn, when you play a
                # Treasure, you may play it again.
                if (
                    not getattr(player, "tiara_replay_used", False)
                    and choice.name != "Tiara"
                    and any(card.name == "Tiara" for card in player.in_play)
                    and choice in player.in_play
                ):
                    if player.ai.should_replay_treasure_with_tiara(
                        self, player, choice
                    ):
                        player.tiara_replay_used = True
                        choice.on_play(self)
                        if self.prophecy is not None and self.prophecy.is_active:
                            self.prophecy.on_play_treasure(self, player, choice)

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

            # Guilds Overpay: ask the AI whether to pay extra coins on top of
            # the printed cost. Only Cards that opt in via ``may_overpay``
            # (e.g. Doctor, Herald, Masterpiece, Stonemason) trigger this.
            overpay_amount = 0
            if (
                not getattr(choice, "is_event", False)
                and not getattr(choice, "is_project", False)
                and choice.may_overpay(self)
                and player.coins > 0
            ):
                max_overpay = max(0, player.coins)
                if max_overpay > 0:
                    chosen = player.ai.choose_overpay_amount(self, player, choice, max_overpay)
                    overpay_amount = max(0, min(int(chosen or 0), max_overpay))
                    if overpay_amount > 0:
                        player.coins -= overpay_amount
                        player.coins_spent_this_turn += overpay_amount
                        self.log_callback(
                            (
                                "action",
                                player.ai.name,
                                f"overpays {overpay_amount} for {choice}",
                                {"overpay": overpay_amount, "remaining_coins": player.coins},
                            )
                        )

            if getattr(choice, "is_event", False):
                choice.on_buy(self, player)
            elif getattr(choice, "is_project", False):
                # Add a copy of the project to the player's owned projects
                player.projects.append(choice)
                choice.on_buy(self, player)
            else:
                # Dark Ages: buying a Knight removes the top of the Knights
                # pile, not a "Sir Bailey" pile.
                pile_name = choice.name
                if choice.is_knight and "Knights" in self.pile_order:
                    pile_name = "Knights"
                    if self.pile_order["Knights"]:
                        self.pile_order["Knights"].pop()
                self.supply[pile_name] = max(0, self.supply.get(pile_name, 0) - 1)
                self.log_callback(("supply_change", pile_name, -1, self.supply[pile_name]))
                choice.on_buy(self)
                gained_card = self.gain_card(player, choice)

                if overpay_amount > 0:
                    choice.on_overpay(self, player, overpay_amount)

                self._handle_on_buy_in_play_effects(player, choice, gained_card)
                self._apply_embargo_tokens(player, choice.name)
                # Dark Ages: Hovel reacts to buying a Victory card.
                if choice.is_victory:
                    self._handle_hovel_reaction(player)
                self._apply_tax_tokens(player, choice.name)

                # Empires Landmarks: react to buys (Basilica, Colonnade, Defiled Shrine).
                for landmark in self.landmarks:
                    landmark.on_buy(self, player, choice)

                # Plunder Nearby trait: +1 Buy when buying from Nearby pile.
                if self.pile_traits.get(choice.name) == "Nearby":
                    player.buys += 1

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
        self.phase = "night"

    def handle_night_phase(self):
        """Play Night cards from hand after Buy, before Cleanup.

        Each Night-card play follows the standard flow: ``on_play`` is called,
        the card moves to in_play, and Duration-Night cards stay in play until
        their start-of-next-turn effect resolves.
        """

        player = self.current_player
        while True:
            night_cards = [card for card in player.hand if card.is_night]
            if not night_cards:
                break

            choice = player.ai.choose_night(self, night_cards + [None])
            if choice is None or choice not in player.hand:
                break

            self.log_callback(("action", player.ai.name, f"plays Night {choice}", {}))
            player.hand.remove(choice)
            player.in_play.append(choice)
            choice.on_play(self)

            # Rising Sun prophecy hooks may also care about Night plays
            if self.prophecy is not None and self.prophecy.is_active:
                if choice.is_action:
                    self.prophecy.on_play_action(self, player, choice)
                if choice.is_attack:
                    self.prophecy.on_play_attack(self, player, choice)

        self.phase = "cleanup"

    def _handle_buy_phase_end(self, player: PlayerState) -> None:
        """Resolve end-of-buy-phase triggers like Treasury and Joust."""
        # Allies: League of Bankers fires before normal end-of-buy hooks
        # so the +$ from Favors can be spent on a leftover buy if any.
        for ally in self.allies:
            hook = getattr(ally, "on_buy_phase_end", None)
            if hook is not None:
                hook(self, player)
        for card in list(player.in_play):
            if hasattr(card, "on_buy_phase_end"):
                card.on_buy_phase_end(self)
            if hasattr(card, "on_cleanup_return_province"):
                card.on_cleanup_return_province(player)

        # Empires Donate: resolve any pending Donate buys at end of buy phase.
        donates = getattr(player, "donate_pending", 0)
        if donates:
            for _ in range(donates):
                self._resolve_donate(player)
            player.donate_pending = 0

        # Renaissance: end-of-buy-phase project triggers (Pageant, Exploration)
        for project in player.projects:
            if hasattr(project, "on_buy_phase_end"):
                project.on_buy_phase_end(self, player)

    def _resolve_donate(self, player: PlayerState) -> None:
        """Empires Donate: dump hand+deck into discard, trash any from
        discard, then put discard into deck and shuffle."""
        import random as _random

        # Move hand and deck into discard.
        player.discard.extend(player.hand)
        player.hand = []
        player.discard.extend(player.deck)
        player.deck = []

        # AI trashes any cards from discard.
        keep = []
        to_trash = []
        for card in list(player.discard):
            choice = player.ai.choose_card_to_trash(self, [card, None])
            if choice is card:
                to_trash.append(card)
            else:
                keep.append(card)
        player.discard = keep
        for card in to_trash:
            self.trash_card(player, card)

        # Put all of discard into deck and shuffle.
        deck = list(player.discard)
        player.discard = []
        _random.shuffle(deck)
        player.deck = deck

        # Draw a fresh hand of 5.
        self.draw_cards(player, 5)

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

        # Rising Sun: Flourishing Trade and other cost-modifying Prophecies.
        if self.prophecy is not None and self.prophecy.is_active:
            cost += self.prophecy.cost_modifier(self, player, card)

        # Plunder Cheap trait: cards from the Cheap pile cost $1 less.
        if self.pile_traits.get(card.name) == "Cheap":
            cost -= 1
        # Allies "Family of Inventors": -$1 cost tokens on Supply piles.
        tokens = getattr(self, "family_inventor_tokens", {}).get(card.name, 0)
        if tokens:
            cost -= tokens

        return max(0, cost)

    def _get_affordable_cards(self, player):
        """Helper to get list of affordable cards, events and projects."""

        if player.debt > 0:
            return []

        affordable = []
        available_coins = player.coins + player.coin_tokens

        for card_name, count in self.supply.items():
            if count > 0:
                # Dark Ages: ordered piles ("Knights", "Ruins") expose the
                # top card as the buyable entry. Ruins is never normally
                # buyable, but Knights is.
                if card_name in self.pile_order:
                    top = self.top_of_pile(card_name)
                    if top is None:
                        continue
                    card = top
                    # The top card of an ordered pile is implicitly buyable
                    # (Knights). Ruins is never bought directly — the only
                    # pile_order pile players can buy from is Knights.
                    pile_buyable = card_name == "Knights"
                else:
                    card = get_card(card_name)
                    pile_buyable = card.may_be_bought(self)
                cost = self.get_card_cost(player, card)
                if (
                    cost <= available_coins
                    and card.cost.potions <= player.potions
                    and pile_buyable
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

        # Rising Sun: Prophecy cleanup-start hook (Biding Time, Sickness)
        if self.prophecy is not None and self.prophecy.is_active:
            self.prophecy.on_cleanup_start(self, player)

        # Rising Sun: Cards in play with cleanup-start triggers (River Shrine)
        for card in list(player.in_play):
            if hasattr(card, "on_cleanup_start"):
                card.on_cleanup_start(self)

        # Allies: end-of-turn / cleanup hook.
        # Used by Coastal Haven, Family of Inventors, Island Folk,
        # Order of Masons.
        for ally in self.allies:
            hook = getattr(ally, "on_turn_end", None)
            if hook is not None:
                hook(self, player)

        # Prosperity 2E: Anvil and similar "when you discard this from play"
        # cards trigger BEFORE the hand is discarded so the player can choose
        # to discard a Treasure from their actual end-of-turn hand. Cards
        # that opt in expose ``on_discard_from_play``; we resolve them here
        # while leaving the card itself in play (the regular cleanup loop
        # below will then discard it normally).
        for card in list(player.in_play):
            if (
                hasattr(card, "on_discard_from_play")
                and card not in player.duration
                and card not in player.multiplied_durations
            ):
                card.on_discard_from_play(self, player)

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

        # Plunder Patient trait: at end of turn, mat cards from Patient pile.
        patient_pile = self.trait_piles.get("Patient")
        if patient_pile:
            patient_cards = [c for c in player.hand if c.name == patient_pile]
            if patient_cards:
                self.patient_mat.setdefault(id(player), []).extend(patient_cards)
                for card in patient_cards:
                    player.hand.remove(card)

        # Plunder Pendant: +$1 per differently-named Treasure in play per Pendant.
        pendants_in_play = [c for c in player.in_play if c.name == "Pendant"]
        if pendants_in_play:
            distinct_treasures = {c.name for c in player.in_play if c.is_treasure}
            for _ in pendants_in_play:
                player.coins += len(distinct_treasures)

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

        tireless_set_aside: list[Card] = []

        for card in in_play_cards:
            if card in durations_to_keep:
                player.in_play.append(card)
            elif getattr(card, "_frog_topdeck", False):
                # Menagerie Way of the Frog: topdeck on cleanup.
                card._frog_topdeck = False
                player.deck.insert(0, card)
            elif (
                card.name == "Walled Village"
                and getattr(player, "walled_villages_played", 0) <= 1
            ):
                player.deck.insert(0, card)
            elif (
                card.name == "Border Guard"
                and getattr(card, "horn_topdeck_pending", False)
            ):
                # Renaissance Horn: topdeck this Border Guard during cleanup.
                card.horn_topdeck_pending = False
                player.deck.insert(0, card)
            elif (
                card.is_treasure
                and getattr(player, "panic_active", False)
                and card.name in self.supply
            ):
                # Rising Sun Panic: discarded Treasures return to their pile
                # (essentially a one-shot Treasure under Panic).
                self.supply[card.name] = self.supply.get(card.name, 0) + 1
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
                # Tireless trait: set aside instead of discarding
                if card.name in self.tireless_piles:
                    tireless_set_aside.append(card)
                else:
                    self.discard_card(player, card, from_cleanup=True)

        if player.trickster_set_aside:
            player.hand.extend(player.trickster_set_aside)
            player.trickster_set_aside = []
        player.trickster_uses_remaining = 0

        # Outpost: schedule an extra turn for this player with a 3-card hand.
        outpost_extra_turn = bool(getattr(player, "outpost_pending", False))
        cards_to_draw = 3 if outpost_extra_turn else 5

        # Nocturne — The River's Gift: +1 Card at end of turn (per active copy)
        rivers_count = sum(
            1 for b in getattr(player, "active_boons", []) if b == "The River's Gift"
        )
        cards_to_draw += rivers_count
        # Allies "Order of Masons" bonus: +1 Card per 2 Favors spent
        # this turn end (banked above before cleanup runs).
        bonus = getattr(player, "order_of_masons_bonus", 0)
        if bonus:
            cards_to_draw += bonus
            player.order_of_masons_bonus = 0

        # Draw new hand
        player.draw_cards(cards_to_draw)

        # Rising Sun Foresight: cards set aside earlier go into hand after
        # drawing the next hand.
        if getattr(player, "foresight_set_aside", None):
            player.hand.extend(player.foresight_set_aside)
            player.foresight_set_aside = []

        # Tireless: put set-aside cards on top of deck after drawing
        for card in tireless_set_aside:
            player.deck.insert(0, card)

        # Nocturne — Faithful Hound: set-aside Hounds return to hand at end of turn
        if getattr(player, "hound_set_aside", None):
            player.hand.extend(player.hound_set_aside)
            player.hound_set_aside = []

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
        player.sailor_play_uses = 0
        player.corsair_trashed_this_turn = False
        # Rotate gain history for Smugglers.
        player.gained_cards_last_turn = list(getattr(player, "gained_cards_this_turn", []))
        player.gained_cards_this_turn = []
        # Outpost bookkeeping.
        player.outpost_taken_last_turn = outpost_extra_turn
        player.outpost_pending = False

        # Move to next player
        if outpost_extra_turn:
            self.extra_turn = True

        if self.fleet_extra_round_active and not self.extra_turn:
            # Fleet extra round: pop the player whose turn just ended and
            # advance to the next Fleet owner in the queue.
            if self.fleet_extra_players and self.fleet_extra_players[0] is player:
                self.fleet_extra_players.pop(0)
            if self.fleet_extra_players:
                next_player = self.fleet_extra_players[0]
                self.current_player_index = self.players.index(next_player)
            self.phase = "start"
            self.extra_turn = False
            return

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
        elif self.phase == "night":
            self.handle_night_phase()
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

        normal_end = (
            self.supply.get("Province", 0) == 0 or self.empty_piles >= 3
        )

        # Renaissance Fleet: if normal end-game would trigger and any player
        # owns Fleet, grant one extra round to all Fleet owners before the
        # game actually ends. Non-Fleet owners are skipped during this round.
        if (
            normal_end
            and not self.fleet_extra_round_active
            and any(
                any(getattr(p, "name", "") == "Fleet" for p in pl.projects)
                for pl in self.players
            )
        ):
            self.fleet_extra_round_active = True
            self.fleet_extra_players = [
                pl for pl in self.players
                if any(getattr(p, "name", "") == "Fleet" for p in pl.projects)
            ]
            self.log_callback("Fleet: extra round of turns for Fleet owners")
            # Move directly to the first Fleet player and resume play.
            if self.fleet_extra_players:
                self.current_player_index = self.players.index(
                    self.fleet_extra_players[0]
                )
                self.phase = "start"
            return False

        # If we are inside the Fleet extra round, end only once every Fleet
        # owner has taken their bonus turn.
        if self.fleet_extra_round_active:
            if self.fleet_extra_players:
                return False
            self._update_final_metrics()
            self.log_callback("Game over (after Fleet extra round)")
            return True

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
        self._handle_friendly_discard(player, card)

    def _handle_friendly_discard(self, player: PlayerState, card: Card) -> None:
        """Friendly: gain a copy from this pile when a Friendly card is discarded."""
        if self.pile_traits.get(card.name) != "Friendly":
            return
        if self.supply.get(card.name, 0) <= 0:
            return
        if getattr(self, "_friendly_processing", False):
            return
        self._friendly_processing = True
        try:
            from ..cards.registry import get_card

            self.supply[card.name] -= 1
            self.gain_card(player, get_card(card.name))
        finally:
            self._friendly_processing = False

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

    # ---- Nocturne Boons ----

    def _ensure_boons_deck(self) -> None:
        from dominion.boons import create_boons_deck

        if not self.boons_deck:
            if self.boons_discard:
                self.boons_deck = list(self.boons_discard)
                random.shuffle(self.boons_deck)
                self.boons_discard = []
            else:
                self.boons_deck = create_boons_deck()

    def draw_boon(self) -> Optional[str]:
        """Draw the next Boon from the Boons deck, shuffling if needed.

        Excludes any Boons currently set aside for Druid or held as a
        persistent active Boon by any player (they are not in the deck).
        """

        self._ensure_boons_deck()
        # Remove any Boon names that are reserved by Druid or actively held
        # by a player from the deck so they aren't drawn.
        reserved: set[str] = set(self.druid_boons)
        for p in self.players:
            for b in getattr(p, "active_boons", []):
                reserved.add(b)
        while self.boons_deck and self.boons_deck[-1] in reserved:
            self.boons_deck.pop()
            self._ensure_boons_deck()
        if not self.boons_deck:
            return None
        return self.boons_deck.pop()

    def discard_boon(self, boon_name: Optional[str]) -> None:
        if boon_name:
            self.boons_discard.append(boon_name)

    def resolve_boon(self, player: "PlayerState", boon_name: str) -> None:
        """Apply Boon ``boon_name`` to ``player`` and log it."""

        if not boon_name:
            return
        from dominion.boons import resolve_boon, is_persistent_boon

        self.log_callback(("action", player.ai.name, f"receives Boon: {boon_name}", {}))
        resolve_boon(boon_name, self, player)

        if is_persistent_boon(boon_name):
            # Persistent Boons hang on the player; they will be returned to
            # the Boons discard pile at start of their next turn.
            if not hasattr(player, "active_boons"):
                player.active_boons = []
            player.active_boons.append(boon_name)
        else:
            self.discard_boon(boon_name)

    def receive_boon(self, player: "PlayerState") -> Optional[str]:
        """Draw and resolve a Boon for ``player``."""

        boon = self.draw_boon()
        if not boon:
            return None
        self.resolve_boon(player, boon)
        return boon

    def setup_druid_boons(self) -> None:
        """Set aside 3 random Boons for Druid for the duration of the game."""

        self._ensure_boons_deck()
        chosen: list[str] = []
        for _ in range(3):
            if not self.boons_deck:
                self._ensure_boons_deck()
            if not self.boons_deck:
                break
            chosen.append(self.boons_deck.pop())
        self.druid_boons = chosen

    def gain_card(
        self,
        player: PlayerState,
        card: Card,
        to_deck: bool = False,
        from_supply: bool = True,
    ) -> Card:
        """Add a card to a player's discard or deck, honoring topdeck effects.

        ``from_supply`` controls supply-restoration semantics. The default
        (``True``) matches the historical contract: the caller has already
        decremented the supply for ``card.name``, so Trader's reaction and
        the Exile-reclamation path may add 1 back when they replace the
        gain. For trash-origin gains (Lurker, Lich), pass ``False`` so the
        supply pile isn't inflated by the restoration logic.

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
                player, card, actual_card, destination_is_deck, from_supply=from_supply
            )

        if not destination_is_deck and getattr(player, "topdeck_gains", False):
            destination_is_deck = True

        if (
            not destination_is_deck
            and getattr(player, "insignia_active", False)
            and player.ai.should_topdeck_with_insignia(self, player, actual_card)
        ):
            destination_is_deck = True

        # Prosperity 2E: Tiara — while in play, gains may be topdecked.
        if (
            not destination_is_deck
            and any(card.name == "Tiara" for card in player.in_play)
            and player.ai.should_topdeck_with_tiara(self, player, actual_card)
        ):
            destination_is_deck = True

        if reclaimed and from_supply and card.name in self.supply:
            # Caller already decremented the supply; restore it since the
            # Exiled card is being used instead. Only valid for from-supply
            # gains — trash-origin gains never decremented in the first place.
            self.supply[card.name] = self.supply.get(card.name, 0) + 1

        if destination_is_deck:
            player.deck.insert(0, actual_card)
        else:
            player.discard.append(actual_card)

        self._handle_gatekeeper_exile(player, actual_card, destination_is_deck, reclaimed)

        actual_card.on_gain(self, player)

        # Rising Sun: Kintsugi event needs to know whether the player has
        # ever gained a Gold.
        if actual_card.name == "Gold":
            player.kintsugi_has_gained_gold = True

        # Rising Sun: Prophecy on-gain hook (Bureaucracy, Growth, Harsh Winter,
        # Progress, Rapid Expansion all care about gains).
        if self.prophecy is not None and self.prophecy.is_active:
            self.prophecy.on_gain(self, player, actual_card)

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
        self._handle_menagerie_gain_reactions(player, actual_card)
        self._handle_opponent_gain_hooks(player, actual_card)
        self._handle_livery_gain(player, actual_card)

        if (
            hasattr(player, "cards_gained_this_buy_phase")
            and player is self.current_player
            and self.phase == "buy"
        ):
            player.cards_gained_this_buy_phase += 1
            if actual_card.is_action or actual_card.is_treasure:
                player.gained_action_or_treasure_this_buy_phase = True

        if actual_card.is_victory and player is self.current_player and self.phase == "buy":
            player.gained_victory_this_buy_phase = True

        # Treasury cares about Victory cards gained anywhere on your turn
        # (Action phase via Workshop / Charm / Ironworks counts too).
        if actual_card.is_victory and player is self.current_player:
            player.gained_victory_this_turn = True

        if hasattr(player, "cards_gained_this_turn"):
            player.cards_gained_this_turn += 1

        # Nocturne — Devil's Workshop and Monastery key off this counter
        if hasattr(player, "cards_gained_this_turn_count"):
            player.cards_gained_this_turn_count += 1

        # Track names of cards gained this turn (for Smugglers).
        if hasattr(player, "gained_cards_this_turn"):
            player.gained_cards_this_turn.append(actual_card.name)

        # Empires Landmarks: react to gains AFTER the counters are bumped so
        # Labyrinth can see cards_gained_this_turn == 2 on the 2nd gain.
        for landmark in self.landmarks:
            landmark.on_gain(self, player, actual_card)

        # Sailor: once per turn, may play a non-Sailor Action gained this turn.
        self._handle_sailor_gain(player, actual_card)

        # Plunder Trait gain hooks (Cursed / Rich / Hasty / Fawning).
        self._handle_trait_on_gain(player, actual_card)

        # Plunder Mirror event: gain another copy of a gained Action.
        self._handle_mirror_gain(player, actual_card)

        # Plunder Landing Party: top-deck this and Treasure on next gain.
        self._handle_landing_party_gain(player, actual_card)

        # Plunder Mining Road: first Treasure gained → gain a Treasure to hand.
        self._handle_mining_road_gain(player, actual_card)
        # Generic "while this is in play, when you gain a card ..." hook used
        # by Allies cards like Galleria and Skirmisher. In-play cards may
        # implement on_owner_gain(game_state, player, gained_card).
        for card in list(player.in_play) + list(player.duration):
            hook = getattr(card, "on_owner_gain", None)
            if hook is not None:
                hook(self, player, actual_card)

        # Allies hook: the chosen Ally may react to the active player's gains
        # (Architects' Guild, Band of Nomads, Trappers' Lodge).
        for ally in self.allies:
            hook = getattr(ally, "on_owner_gain", None)
            if hook is not None:
                hook(self, player, actual_card)

        return actual_card

    def _handle_sailor_gain(self, player: PlayerState, gained_card: Card) -> None:
        """Trigger Sailor's "may play this gain" effect for the gainer's own gains."""
        if getattr(player, "sailor_play_uses", 0) <= 0:
            return
        for card in list(player.duration):
            if card.name == "Sailor" and hasattr(card, "on_gain_for_owner"):
                if card.on_gain_for_owner(self, player, gained_card):
                    return

    def _handle_trait_on_gain(self, player: PlayerState, gained_card: Card) -> None:
        """Resolve Plunder Trait reactions to a gain."""
        from ..cards.registry import get_card

        trait = self.pile_traits.get(gained_card.name)
        if trait == "Cursed":
            self._gain_random_loot(player)
            self.give_curse_to_player(player)

        if trait == "Rich":
            if self.supply.get("Silver", 0) > 0:
                self.supply["Silver"] -= 1
                self.gain_card(player, get_card("Silver"))

        if trait == "Hasty":
            zone = None
            if gained_card in player.discard:
                zone = player.discard
            elif gained_card in player.deck:
                zone = player.deck
            if zone is not None:
                zone.remove(gained_card)
                self.hasty_set_aside.setdefault(id(player), []).append(gained_card)

        if gained_card.name == "Province":
            fawning_pile = self.trait_piles.get("Fawning")
            if fawning_pile and self.supply.get(fawning_pile, 0) > 0:
                self.supply[fawning_pile] -= 1
                self.gain_card(player, get_card(fawning_pile))

    def _gain_random_loot(self, player: PlayerState):
        """Gain a random face-up Loot."""
        import random

        from ..cards.registry import get_card
        from ..cards.plunder import LOOT_CARD_NAMES

        loot_name = random.choice(LOOT_CARD_NAMES)
        return self.gain_card(player, get_card(loot_name))

    def _handle_mirror_gain(self, player: PlayerState, gained_card: Card) -> None:
        if not gained_card.is_action:
            return
        pending = self.mirror_pending.get(id(player), 0)
        if pending <= 0:
            return
        self.mirror_pending[id(player)] = 0
        if self.supply.get(gained_card.name, 0) <= 0:
            return
        from ..cards.registry import get_card

        self.supply[gained_card.name] -= 1
        self.gain_card(player, get_card(gained_card.name))

    def _handle_landing_party_gain(self, player: PlayerState, gained_card: Card) -> None:
        if not gained_card.is_treasure:
            return
        pending = self.landing_party_pending.get(id(player))
        if not pending:
            return
        landing = pending.pop(0)
        if gained_card in player.discard:
            player.discard.remove(gained_card)
        elif gained_card in player.deck:
            player.deck.remove(gained_card)
        else:
            pending.insert(0, landing)
            return
        if landing in player.duration:
            player.duration.remove(landing)
        if landing in player.in_play:
            player.in_play.remove(landing)
        player.deck.append(landing)
        player.deck.append(gained_card)

    def _handle_mining_road_gain(self, player: PlayerState, gained_card: Card) -> None:
        if player is not self.current_player:
            return
        if not gained_card.is_treasure:
            return
        if not any(card.name == "Mining Road" for card in player.in_play):
            return
        if getattr(player, "mining_road_triggered", False):
            return
        player.mining_road_triggered = True
        from ..cards.registry import get_card

        candidates = []
        for name, count in self.supply.items():
            if count <= 0:
                continue
            try:
                card = get_card(name)
            except ValueError:
                continue
            if card.is_treasure:
                candidates.append(card)
        if not candidates:
            return
        candidates.sort(key=lambda c: (c.cost.coins, c.name), reverse=True)
        choice = candidates[0]
        self.supply[choice.name] -= 1
        gained = self.gain_card(player, choice)
        if gained in player.discard:
            player.discard.remove(gained)
            player.hand.append(gained)
        elif gained in player.deck:
            player.deck.remove(gained)
            player.hand.append(gained)

    def _handle_gatekeeper_exile(
        self, player: PlayerState, card: Card, on_deck: bool, reclaimed: "Card | None"
    ) -> None:
        """Exile a gained Action/Treasure if the player is under Gatekeeper attack."""
        if getattr(player, "gatekeeper_attacks", 0) <= 0:
            return
        if not (card.is_action or card.is_treasure):
            return
        # Skip if player already had a copy in exile (reclaimed counts)
        if reclaimed or any(c.name == card.name for c in player.exile):
            return

        # Move card from its current location to exile
        if on_deck and card in player.deck:
            player.deck.remove(card)
        elif card in player.discard:
            player.discard.remove(card)
        else:
            return
        player.exile.append(card)

    def _handle_trader_exchange(
        self,
        player: PlayerState,
        original_card: Card,
        actual_card: Card,
        to_deck: bool,
        from_supply: bool = True,
    ) -> Card:
        """Allow Trader reactions to replace a gain with a Silver.

        ``from_supply`` mirrors ``gain_card``: when the caller decremented
        supply for ``original_card`` (the normal case), Trader restores it.
        For trash-origin gains the caller never touched supply so we must
        not "restore" a count that was never decremented.
        """

        if self.supply.get("Silver", 0) <= 0:
            return actual_card

        if not any(card.name == "Trader" for card in player.hand):
            return actual_card

        if not player.ai.should_reveal_trader(self, player, original_card, to_deck=to_deck):
            return actual_card

        if from_supply and original_card.name in self.supply:
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
            player.actions_gained_this_turn == 3
            and not player.cauldron_triggered
            and any(card_in_play.name == "Cauldron" for card_in_play in player.in_play)
        ):
            player.cauldron_triggered = True

            cauldron_card = next(
                (c for c in player.in_play if c.name == "Cauldron"),
                None,
            )

            self.log_callback(
                (
                    "action",
                    player.ai.name,
                    "Cauldron triggers (3rd Action gained)",
                    {},
                )
            )

            def curse_target(target):
                if self.supply.get("Curse", 0) <= 0:
                    return
                self.give_curse_to_player(target)
                target_name = (
                    self.logger.format_player_name(target.ai.name)
                    if self.logger
                    else target.ai.name
                )
                self.log_callback(
                    (
                        "action",
                        player.ai.name,
                        f"Cauldron gives curse to {target_name}",
                        {"curses_remaining": self.supply.get("Curse", 0)},
                    )
                )

            for other in self.players:
                if other is player:
                    continue
                self.attack_player(
                    other,
                    curse_target,
                    attacker=player,
                    attack_card=cauldron_card,
                )

    def player_has_shield(self, player: PlayerState) -> bool:
        """Check if the player has a Shield card in hand."""
        return any(card.name == "Shield" for card in player.hand)

    def attack_player(
        self,
        target: PlayerState,
        attack_fn,
        *,
        attacker: PlayerState = None,
        attack_card: Card = None,
    ) -> None:
        """Apply an attack to a player unless blocked by reactions."""
        self._maybe_play_guard_dogs(target)
        if attacker is None:
            attacker = self.current_player
        # Some Reactions modify the target's hand before the attack hits
        # (Diplomat, Secret Chamber). They don't block the attack itself.
        self._maybe_react_diplomat(target)
        self._maybe_react_secret_chamber(target)
        if self._player_blocks_attack(target, attacker, attack_card):
            return

        attack_fn(target)

    def _maybe_react_diplomat(self, player: PlayerState) -> None:
        """Resolve Diplomat reactions: with hand of 5+, draw 2 then discard 3.

        The Reaction is legal to reveal repeatedly while the hand still
        has 5+ cards and a Diplomat in it (including re-revealing the
        same copy). We loop until the AI declines, the hand drops
        below 5, or no Diplomat is available — with a hard safety cap
        to prevent any pathological infinite loop.
        """
        max_reveals = 32  # safety bound; well above any realistic deck.
        for _ in range(max_reveals):
            if not any(card.name == "Diplomat" for card in player.hand):
                return
            if len(player.hand) < 5:
                return
            if not player.ai.should_reveal_diplomat(self, player):
                return

            self.log_callback(
                ("action", player.ai.name, "reveals Diplomat to react", {})
            )
            self.draw_cards(player, 2)
            # Now discard 3 chosen cards.
            discards = player.ai.choose_cards_to_discard(
                self, player, list(player.hand), 3, reason="diplomat"
            )
            actually_discarded: list[Card] = []
            for card in discards[:3]:
                if card in player.hand:
                    player.hand.remove(card)
                    self.discard_card(player, card)
                    actually_discarded.append(card)
            # If the AI returned fewer than 3 picks, fall back to forcing
            # discards (the rule text says "discard 3").
            while len(actually_discarded) < 3 and player.hand:
                fallback = min(player.hand, key=lambda c: (c.cost.coins, c.name))
                player.hand.remove(fallback)
                self.discard_card(player, fallback)
                actually_discarded.append(fallback)

    def _maybe_react_secret_chamber(self, player: PlayerState) -> None:
        """Resolve Secret Chamber reactions: +2 cards, then put 2 onto deck.

        The Reaction can be revealed multiple times for one Attack
        trigger (and may interleave with other Reactions drawn during
        resolution). Loop until the AI declines or no Secret Chamber
        remains in hand, with a safety cap.
        """
        max_reveals = 32  # safety bound.
        reveal_count = 0
        for _ in range(max_reveals):
            if not any(card.name == "Secret Chamber" for card in player.hand):
                return
            try:
                want_reveal = player.ai.should_discard_secret_chamber(
                    self, player, reveal_count=reveal_count
                )
            except TypeError:
                # Older AI overrides may not accept reveal_count.
                want_reveal = player.ai.should_discard_secret_chamber(self, player)
            if not want_reveal:
                return
            reveal_count += 1

            self.log_callback(
                ("action", player.ai.name, "reveals Secret Chamber to react", {})
            )
            self.draw_cards(player, 2)
            if not player.hand:
                return
            topdeck_picks = player.ai.choose_secret_chamber_topdeck(
                self, player, list(player.hand)
            )
            placed = 0
            for card in topdeck_picks:
                if placed >= 2:
                    break
                if card in player.hand:
                    player.hand.remove(card)
                    player.deck.append(card)
                    placed += 1
            # If AI didn't pick enough, top-deck cheapest cards.
            while placed < 2 and player.hand:
                fallback = min(player.hand, key=lambda c: (c.cost.coins, c.name))
                player.hand.remove(fallback)
                player.deck.append(fallback)
                placed += 1

    def _player_blocks_attack(
        self,
        player: PlayerState,
        attacker: PlayerState = None,
        attack_card: Card = None,
    ) -> bool:
        if self.player_has_shield(player):
            self.log_callback(("action", player.ai.name, "reveals Shield to block the attack", {}))
            return True

        if any(card.name == "Lighthouse" for card in player.duration):
            self.log_callback(("action", player.ai.name, "is protected by Lighthouse", {}))
            return True

        if any(card.name == "Guardian" for card in player.duration):
            self.log_callback(("action", player.ai.name, "is protected by Guardian", {}))
            return True

        # Generic Reaction-card dispatch: any Reaction card in hand may
        # provide a `react_to_attack` override that returns True to block.
        # Iterate over a snapshot — react_to_attack must not mutate the hand
        # mid-iteration in the default implementations.
        for card in list(player.hand):
            if not card.is_reaction:
                continue
            try:
                blocked = card.react_to_attack(self, player, attacker, attack_card)
            except TypeError:
                # Backwards-compatibility: a reaction card without the new
                # signature shouldn't crash the attack pipeline.
                blocked = False
            if blocked:
                return True

        # Cornucopia: Young Witch may be blocked by revealing the Bane card.
        # The Bane is any (non-Reaction) card the Bane pile designates; only
        # blocks Young Witch attacks (not other attacks).
        if (
            attack_card is not None
            and attack_card.name == "Young Witch"
            and self.bane_card_name
        ):
            for card in player.hand:
                if card.name == self.bane_card_name:
                    if player.ai.should_reveal_bane(self, player):
                        self.log_callback(
                            (
                                "action",
                                player.ai.name,
                                f"reveals {card.name} (Bane) to block Young Witch",
                                {
                                    "attacker": attacker.ai.name if attacker else None,
                                },
                            )
                        )
                        return True
                    break

        return False

    def trash_card(self, player: PlayerState, card: Card) -> None:
        """Move a card to the trash and trigger related effects."""
        self.trash.append(card)
        card.on_trash(self, player)

        # Resolve project triggers for trashing
        for project in player.projects:
            if hasattr(project, "on_trash"):
                project.on_trash(self, player, card)

        # Empires Landmarks (Tomb).
        for landmark in self.landmarks:
            landmark.on_trash(self, player, card)

        # Renaissance Priest: +$2 for each Priest played this turn.
        priest_count = getattr(player, "priest_played_this_turn", 0)
        if priest_count and player is self.current_player:
            player.coins += 2 * priest_count

        # Plunder Crucible: track trashes-this-turn.
        if player is self.current_player:
            player.cards_trashed_this_turn = getattr(player, "cards_trashed_this_turn", 0) + 1

        # Plunder Pious trait.
        self._handle_pious_trash(player, card)

        self._handle_market_square_reaction(player, card)

    def _handle_hovel_reaction(self, player: PlayerState) -> None:
        """Offer Hovels in hand the chance to trash themselves on Victory buys."""
        while True:
            hovels = [card for card in player.hand if card.name == "Hovel"]
            if not hovels:
                return
            if not player.ai.should_trash_hovel_on_victory(self, player):
                return
            hovel = hovels[0]
            player.hand.remove(hovel)
            self.trash_card(player, hovel)

    def _handle_pious_trash(self, trasher: PlayerState, trashed_card: Card) -> None:
        if getattr(self, "_pious_processing", False):
            return
        pious_pile = self.trait_piles.get("Pious")
        if not pious_pile:
            return
        if self.supply.get(pious_pile, 0) <= 0:
            return
        self._pious_processing = True
        try:
            from ..cards.registry import get_card

            self.supply[pious_pile] -= 1
            self.trash_card(trasher, get_card(pious_pile))
        finally:
            self._pious_processing = False

    def _handle_market_square_reaction(self, player: PlayerState, trashed_card: Card) -> None:
        """Offer Market Square reactions for any card the player just trashed."""

        from ..cards.registry import get_card

        while True:
            squares = [card for card in player.hand if card.name == "Market Square"]
            if not squares:
                return
            if self.supply.get("Gold", 0) <= 0:
                return
            if not player.ai.should_react_with_market_square(self, player, trashed_card):
                return

            square = squares[0]
            player.hand.remove(square)
            self.discard_card(player, square)
            self.supply["Gold"] -= 1
            self.gain_card(player, get_card("Gold"))

    def _handle_cargo_ship_gain(self, player: PlayerState, gained_card: Card) -> None:
        """Check if a Cargo Ship in play wants to set aside the gained card."""
        for card in list(player.in_play):
            if hasattr(card, "on_cargo_ship_gain"):
                if card.on_cargo_ship_gain(self, player, gained_card):
                    break

    def _handle_opponent_gain_hooks(self, gainer: PlayerState, gained_card: Card) -> None:
        """Resolve project / duration / hand-reaction hooks that trigger when
        another player gains a card.
        """
        for player in self.players:
            if player is gainer:
                continue
            for project in player.projects:
                if hasattr(project, "on_opponent_gain"):
                    project.on_opponent_gain(self, player, gained_card)
            # Duration cards (Monkey, Blockade) can react to opponent gains.
            for card in list(player.duration):
                if hasattr(card, "on_opponent_gain"):
                    card.on_opponent_gain(self, player, gainer, gained_card)
            # Menagerie: Black Cat and Falconer (in-hand reactions to opponent gains)
            for card in list(player.hand):
                if hasattr(card, "on_opponent_gain"):
                    card.on_opponent_gain(self, player, gainer, gained_card)

    def _handle_menagerie_gain_reactions(
        self, player: PlayerState, gained_card: Card
    ) -> None:
        """Sleigh / Sheepdog reactions in the gainer's own hand."""
        # Sleigh: discard from hand to put gained card into hand or onto deck
        for card in list(player.hand):
            if card.name == "Sleigh" and hasattr(card, "react_to_own_gain"):
                decision = card.react_to_own_gain(self, player, gained_card)
                if decision in {"hand", "deck"}:
                    if gained_card in player.discard:
                        player.discard.remove(gained_card)
                    elif gained_card in player.deck:
                        player.deck.remove(gained_card)
                    if decision == "hand":
                        player.hand.append(gained_card)
                    else:
                        player.deck.append(gained_card)
                    break
        # Sheepdog: play from hand when you gain a card
        for card in list(player.hand):
            if card.name == "Sheepdog" and hasattr(card, "react_to_own_gain"):
                if card.react_to_own_gain(self, player, gained_card):
                    break

    def _maybe_kiln_gain(self, player: PlayerState, played_card: Card) -> None:
        """Menagerie Kiln: gain a copy of the next card the player plays.

        Triggers once per pending Kiln charge per card play.
        """
        pending = getattr(player, "kiln_pending", 0)
        if pending <= 0:
            return
        # Don't trigger on Kiln itself when it would re-trigger on its own play.
        if played_card.name == "Kiln":
            return
        if self.supply.get(played_card.name, 0) <= 0:
            return
        from ..cards.registry import get_card

        if not player.ai.should_gain_copy_with_kiln(self, player, played_card):
            return
        player.kiln_pending = pending - 1
        try:
            copy = get_card(played_card.name)
        except ValueError:
            return
        self.supply[played_card.name] -= 1
        self.gain_card(player, copy)

    def _handle_livery_gain(self, player: PlayerState, gained_card: Card) -> None:
        """Each Livery in play: gain a Horse when a card costing $4+ is gained."""
        if gained_card.name == "Horse":
            return
        if gained_card.cost.coins < 4:
            return
        livery_count = sum(1 for c in player.in_play if c.name == "Livery")
        if livery_count <= 0:
            return
        from ..cards.registry import get_card

        for _ in range(livery_count):
            if self.supply.get("Horse", 0) <= 0:
                break
            self.supply["Horse"] -= 1
            self.gain_card(player, get_card("Horse"))

    def _maybe_corsair_trash(self, treasure_player: PlayerState, treasure_card: Card) -> bool:
        """Let any opposing Corsair trash the first Silver/Gold of the turn."""
        if treasure_card.name not in {"Silver", "Gold"}:
            return False
        if getattr(treasure_player, "corsair_trashed_this_turn", False):
            return False

        for other in self.players:
            if other is treasure_player:
                continue
            for card in list(other.duration):
                if card.name == "Corsair" and hasattr(card, "react_to_treasure_played"):
                    if card.react_to_treasure_played(self, treasure_player, treasure_card):
                        return True
        return False

    def _apply_tax_tokens(self, buyer: PlayerState, card_name: str) -> None:
        """Empires Tax: buyer takes any debt tokens from the pile, then the pile resets."""
        tokens = self.tax_tokens.get(card_name, 0)
        if tokens > 0:
            buyer.debt += tokens
            self.tax_tokens[card_name] = 0

    def _setup_nocturne_extras(self, kingdom_cards: list[Card]) -> None:
        """Add non-supply piles needed by Nocturne kingdom cards."""

        for card in kingdom_cards:
            extras: dict[str, int] = getattr(card, "nocturne_piles", {})
            for name, count in extras.items():
                if name not in self.supply:
                    self.supply[name] = count
        needs_boons = any(getattr(c, "uses_boons", False) for c in kingdom_cards)
        if needs_boons and "Will-o'-Wisp" not in self.supply:
            try:
                wisp = get_card("Will-o'-Wisp")
                self.supply["Will-o'-Wisp"] = wisp.starting_supply(self)
            except ValueError:
                pass

    def _apply_embargo_tokens(self, buyer: PlayerState, card_name: str) -> None:
        """Give the buyer a Curse for each Embargo token on the bought pile."""
        from ..cards.registry import get_card

        tokens = self.embargo_tokens.get(card_name, 0)
        for _ in range(tokens):
            if self.supply.get("Curse", 0) <= 0:
                break
            self.supply["Curse"] -= 1
            self.gain_card(buyer, get_card("Curse"))

    def take_artifact(self, player: PlayerState, name: str) -> None:
        """Transfer the named Artifact to ``player``.

        No-op if the Artifact isn't in the game. Already-held by this
        player → still calls ``on_take`` for symmetry. Held by someone
        else → previous holder's ``on_lose`` fires first.
        """

        artifact = self.artifacts.get(name)
        if artifact is None:
            return
        previous = artifact.holder
        if previous is player:
            return
        if previous is not None:
            artifact.on_lose(self, previous)
        artifact.holder = player
        artifact.on_take(self, player)
        self.log_callback(
            ("action", player.ai.name, f"takes the {name}", {"artifact": name})
        )

    def _update_final_metrics(self):
        """Update final game metrics including victory points."""
        if not self.logger:
            return

        # Calculate and store final victory points for each player
        for player in self.players:
            vp = player.get_victory_points(self)
            self.logger.current_metrics.victory_points[player.ai.name] = vp

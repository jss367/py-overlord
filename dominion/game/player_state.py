import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from dominion.cards.base_card import Card
from dominion.cards.registry import get_card


@dataclass
class PlayerState:
    ai: "AI"  # Type annotation as string to avoid circular import

    # Resources
    actions: int = 1
    buys: int = 1
    coins: int = 0
    coin_tokens: int = 0
    potions: int = 0
    debt: int = 0

    # Card collections
    hand: list[Card] = field(default_factory=list)
    deck: list[Card] = field(default_factory=list)
    discard: list[Card] = field(default_factory=list)
    in_play: list[Card] = field(default_factory=list)
    duration: list[Card] = field(default_factory=list)
    multiplied_durations: list[Card] = field(default_factory=list)
    projects: list = field(default_factory=list)
    exile: list[Card] = field(default_factory=list)
    invested_exile: list[Card] = field(default_factory=list)

    # States and hex penalties
    deluded: bool = False
    envious: bool = False
    misery: int = 0
    cannot_buy_actions: bool = False
    envious_effect_active: bool = False

    # Misc counters
    vp_tokens: int = 0
    villagers: int = 0
    favors: int = 0
    miser_coppers: int = 0
    native_village_mat: list[Card] = field(default_factory=list)
    island_mat: list[Card] = field(default_factory=list)
    pirate_ship_tokens: int = 0
    sailor_play_uses: int = 0
    outpost_pending: bool = False
    outpost_taken_last_turn: bool = False
    corsair_trashed_this_turn: bool = False
    gained_cards_this_turn: list[str] = field(default_factory=list)
    gained_cards_last_turn: list[str] = field(default_factory=list)
    ignore_action_bonuses: bool = False
    collection_played: int = 0
    goons_played: int = 0
    merchant_guilds_played: int = 0
    cost_reduction: int = 0
    innovation_used: bool = False
    journey_token_face_up: bool = True
    groundskeeper_bonus: int = 0
    crossroads_played: int = 0
    fools_gold_played: int = 0
    actions_gained_this_turn: int = 0
    cauldron_triggered: bool = False
    trickster_uses_remaining: int = 0
    trickster_set_aside: list[Card] = field(default_factory=list)
    charm_next_buy_copies: int = 0
    walled_villages_played: int = 0
    fortune_doubled_this_turn: bool = False
    # Empires Enchantress: opponent's first Action play this turn is replaced.
    enchantress_active: bool = False
    enchantress_used_this_turn: bool = False
    # Empires Donate: count of pending Donate events to resolve at end of buy.
    donate_pending: int = 0
    # Rising Sun: Daimyo replays the next non-Command Action card played
    daimyo_pending: int = 0
    continue_used_this_turn: bool = False
    foresight_set_aside: list = field(default_factory=list)
    # Rising Sun: Kintsugi event cares whether Gold has ever been gained.
    kintsugi_has_gained_gold: bool = False
    # Rising Sun: Prophecy-driven per-player state
    biding_time_set_aside: list = field(default_factory=list)
    good_harvest_treasures_played: set = field(default_factory=set)
    panic_active: bool = False
    rapid_expansion_set_aside: list = field(default_factory=list)
    flourishing_trade_active: bool = False

    # Turn tracking
    turns_taken: int = 0
    actions_played: int = 0
    actions_this_turn: int = 0
    coins_spent_this_turn: int = 0
    bought_this_turn: list[str] = field(default_factory=list)
    banned_buys: list[str] = field(default_factory=list)
    delayed_cards: list[Card] = field(default_factory=list)
    seize_the_day_used: bool = False
    topdeck_gains: bool = False
    gained_five_this_turn: bool = False
    gained_five_last_turn: bool = False
    cards_gained_this_turn: int = 0
    cards_gained_this_buy_phase: int = 0
    gained_victory_this_buy_phase: bool = False
    gained_victory_this_turn: bool = False
    flagship_pending: list[Card] = field(default_factory=list)
    highwayman_attacks: int = 0
    highwayman_blocked_this_turn: bool = False
    insignia_active: bool = False
    # Plunder cards / events / traits.
    fated_pile: str = ""
    cards_trashed_this_turn: int = 0
    mining_road_triggered: bool = False
    search_triggered: bool = False
    avoid_pending: int = 0
    deliver_pending: list = field(default_factory=list)
    bury_mat: list = field(default_factory=list)
    prepare_set_aside: list = field(default_factory=list)
    cage_state: object = None
    grotto_set_aside: list = field(default_factory=list)
    # Prosperity 2E: Tiara grants once-per-turn replay-treasure
    tiara_replay_used: bool = False
    # Prosperity 2E: War Chest tracks names already used this turn
    war_chest_named_this_turn: list[str] = field(default_factory=list)
    # Prosperity 2E: Clerk attack — duration self-replay
    clerk_pending_replay: list[Card] = field(default_factory=list)
    # Intrigue 1E: each Coppersmith played gives a +$1 bonus per Copper played.
    coppersmiths_played: int = 0
    # Renaissance Priest: rest-of-turn +$2 on trash trigger.
    priest_played_this_turn: int = 0
    # Renaissance Cargo Ship / Buy phase end tracking
    gained_action_or_treasure_this_buy_phase: bool = False
    # Nocturne — persistent Boons received this/last turn.
    active_boons: list[str] = field(default_factory=list)
    # Nocturne — persistent Boons received via Druid. These behave like
    # ``active_boons`` for purposes of next-turn effects (Field/Forest) and
    # cleanup-time draws (River) but they are NEVER discarded — Druid's three
    # Boons stay set aside for the entire game.
    druid_active_boons: list[str] = field(default_factory=list)
    # Nocturne — Lost in the Woods state from Fool.
    lost_in_the_woods: bool = False
    # Nocturne — Cards gained this turn (count). Used by Devil's Workshop, Monastery.
    cards_gained_this_turn_count: int = 0
    # Nocturne — pending start-of-next-turn effects.
    pending_cobbler_gains: int = 0
    pending_den_of_sin_draws: int = 0
    pending_ghost_town_actions: int = 0
    pending_guardian_coins: int = 0
    pending_secret_cave_coins: int = 0
    pending_raider_coins: int = 0
    # Nocturne Ghost duration: list of set-aside Actions to replay.
    ghost_pending_actions: list = field(default_factory=list)
    # Nocturne — Boons pending at start of next turn (Blessed Village).
    pending_blessed_boons: int = 0

    def initialize(self, use_shelters: bool = False, heirlooms: list[str] = None):
        """Set up starting deck and draw initial hand.

        If ``use_shelters`` is ``True``, start with Necropolis, Hovel and
        Overgrown Estate instead of three Estates as in the Dark Ages expansion.

        ``heirlooms`` is a list of Heirloom card names (Nocturne). For each
        heirloom, one starting Copper is replaced with the matching Heirloom.
        """

        # Create starting deck
        coppers_count = 7
        heirlooms = heirlooms or []
        coppers_count -= len(heirlooms)
        coppers_count = max(0, coppers_count)
        self.deck = [get_card("Copper") for _ in range(coppers_count)]
        for h in heirlooms:
            try:
                self.deck.append(get_card(h))
            except ValueError:
                self.deck.append(get_card("Copper"))
        if use_shelters:
            self.deck += [
                get_card("Necropolis"),
                get_card("Hovel"),
                get_card("Overgrown Estate"),
            ]
        else:
            self.deck += [get_card("Estate") for _ in range(3)]

        # Shuffle the deck
        random.shuffle(self.deck)

        # Reset other collections
        self.hand = []
        self.discard = []
        self.in_play = []
        self.duration = []
        self.multiplied_durations = []
        self.projects = []
        self.exile = []
        self.invested_exile = []

        # Reset resources
        self.actions = 1
        self.buys = 1
        self.coins = 0
        self.coin_tokens = 0
        self.potions = 0
        self.debt = 0
        self.vp_tokens = 0
        self.villagers = 0
        self.miser_coppers = 0
        self.native_village_mat = []
        self.island_mat = []
        self.pirate_ship_tokens = 0
        self.sailor_play_uses = 0
        self.outpost_pending = False
        self.outpost_taken_last_turn = False
        self.corsair_trashed_this_turn = False
        self.gained_cards_this_turn = []
        self.gained_cards_last_turn = []
        self.ignore_action_bonuses = False
        self.collection_played = 0
        self.goons_played = 0
        self.merchant_guilds_played = 0
        self.cost_reduction = 0
        self.innovation_used = False
        self.journey_token_face_up = True
        self.groundskeeper_bonus = 0
        self.crossroads_played = 0
        self.fools_gold_played = 0
        self.actions_gained_this_turn = 0
        self.cauldron_triggered = False
        self.trickster_uses_remaining = 0
        self.trickster_set_aside = []
        self.charm_next_buy_copies = 0
        self.walled_villages_played = 0
        self.fortune_doubled_this_turn = False
        # Enchantress flags persist across turns (cleared by caster's duration
        # trigger), but reset here for game start.
        self.enchantress_active = False
        self.enchantress_used_this_turn = False
        self.donate_pending = 0
        self.daimyo_pending = 0
        self.continue_used_this_turn = False
        self.foresight_set_aside = []
        self.kintsugi_has_gained_gold = False
        self.biding_time_set_aside = []
        self.good_harvest_treasures_played = set()
        self.panic_active = False
        self.rapid_expansion_set_aside = []
        self.flourishing_trade_active = False
        self.turns_taken = 0
        self.actions_played = 0
        self.actions_this_turn = 0
        self.coins_spent_this_turn = 0
        self.bought_this_turn = []
        self.banned_buys = []
        self.delayed_cards = []
        self.seize_the_day_used = False
        self.topdeck_gains = False
        self.gained_five_this_turn = False
        self.gained_five_last_turn = False
        self.cards_gained_this_turn = 0
        self.cards_gained_this_buy_phase = 0
        self.gained_victory_this_buy_phase = False
        self.gained_victory_this_turn = False
        self.flagship_pending = []
        self.highwayman_attacks = 0
        self.highwayman_blocked_this_turn = False
        self.insignia_active = False
        self.cards_trashed_this_turn = 0
        self.mining_road_triggered = False
        self.search_triggered = False
        self.avoid_pending = 0
        self.deliver_pending = []
        self.bury_mat = []
        self.prepare_set_aside = []
        self.cage_state = None
        self.grotto_set_aside = []
        self.tiara_replay_used = False
        self.war_chest_named_this_turn = []
        self.clerk_pending_replay = []
        self.gained_victory_this_buy_phase = False
        self.deluded = False
        self.envious = False
        self.misery = 0
        self.cannot_buy_actions = False
        self.envious_effect_active = False
        self.coppersmiths_played = 0
        self.priest_played_this_turn = 0
        self.gained_action_or_treasure_this_buy_phase = False
        self.active_boons = []
        self.druid_active_boons = []
        self.lost_in_the_woods = False
        self.cards_gained_this_turn_count = 0
        self.pending_cobbler_gains = 0
        self.pending_den_of_sin_draws = 0
        self.pending_ghost_town_actions = 0
        self.pending_guardian_coins = 0
        self.pending_secret_cave_coins = 0
        self.pending_raider_coins = 0
        self.ghost_pending_actions = []
        self.pending_blessed_boons = 0

        # Draw initial hand of 5 cards
        self.draw_cards(5)

    def draw_cards(self, count: int) -> list[Card]:
        """Draw specified number of cards from deck, shuffling if needed."""
        drawn = []

        while len(drawn) < count:
            # If deck is empty, shuffle discard pile
            if not self.deck and self.discard:
                self.shuffle_discard_into_deck()

            # Stop if no cards left
            if not self.deck:
                break

            # Draw a card
            card = self.deck.pop()
            drawn.append(card)
            self.hand.append(card)

        return drawn

    def shuffle_discard_into_deck(self):
        """Shuffle discard pile to create new deck.

        Respects Stash (top), Rising Sun Shadow cards (bottom), Plunder
        Avoid event (top up to 3), and Plunder Fated trait (top of deck).
        Cards at index 0 are the bottom of the deck (drawn last); cards at
        the end are the top (drawn first via ``deck.pop()``).
        """
        avoid_set_aside: list = []
        if self.avoid_pending > 0 and self.discard:
            n = min(3, len(self.discard))
            avoid_set_aside = self.discard[-n:]
            self.discard = self.discard[:-n]
            self.avoid_pending = max(0, self.avoid_pending - 1)
        fated_top: list = []
        if self.fated_pile:
            others_kept = []
            for card in self.discard:
                if card.name == self.fated_pile:
                    fated_top.append(card)
                else:
                    others_kept.append(card)
            self.discard = others_kept
        stash_cards = [card for card in self.discard if card.name == "Stash"]
        shadows = [
            card
            for card in self.discard
            if card.name != "Stash" and getattr(card, "is_shadow", False)
        ]
        others = [
            card
            for card in self.discard
            if card.name != "Stash" and not getattr(card, "is_shadow", False)
        ]
        random.shuffle(others)
        self.deck = shadows + others + stash_cards + fated_top + avoid_set_aside
        self.discard = []

    def count_in_deck(self, card_name: str) -> int:
        """Count total copies of named card across all piles."""
        return sum(1 for card in self.all_cards() if card.name == card_name)

    # Alias used by strategy condition evaluation
    def count(self, card_name: str) -> int:
        return self.count_in_deck(card_name)

    def get_victory_points(self, _game_state=None) -> int:
        """Calculate total victory points for the player.

        Empires Landmarks contribute via ``vp_for(game_state, player)``; Allies
        like Plateau Shepherds may contribute via ``score_bonus``. Both
        require a ``game_state`` argument, but most callers (winner selection,
        end-of-game reports, RL evaluators) call this with no argument. We
        fall back to the player's stored ``game_state`` back-reference so
        Landmarks and Allies are always counted in real games. Tests that
        instantiate a bare ``PlayerState`` will simply get the no-game
        behaviour, which is what they expect.
        """
        total = (
            sum(card.get_victory_points(self) for card in self.all_cards())
            + self.vp_tokens
            - 2 * self.misery
        )
        if _game_state is None:
            _game_state = getattr(self, "game_state", None)
        if _game_state is not None:
            for landmark in getattr(_game_state, "landmarks", []) or []:
                total += landmark.vp_for(_game_state, self)
            for ally in getattr(_game_state, "allies", []) or []:
                hook = getattr(ally, "score_bonus", None)
                if hook is not None:
                    total += hook(_game_state, self)
        return total

    def all_cards(self) -> list[Card]:
        """Return a list of all cards the player possesses."""
        zones = [
            self.hand,
            self.deck,
            self.discard,
            self.in_play,
            self.duration,
            self.multiplied_durations,
            self.exile,
            self.invested_exile,
            self.native_village_mat,
            self.island_mat,
            self.trickster_set_aside,
            self.delayed_cards,
            self.flagship_pending,
            self.clerk_pending_replay,
        ]

        cards: list[Card] = []
        seen_ids: set[int] = set()
        for zone in zones:
            for card in zone:
                card_id = id(card)
                if card_id in seen_ids:
                    continue
                seen_ids.add(card_id)
                cards.append(card)

        return cards

    def get_vp_breakdown(self) -> dict[str, dict[str, int]]:
        """Return a breakdown of victory points by card name."""
        from collections import defaultdict

        counts: dict[str, int] = defaultdict(int)
        points: dict[str, int] = defaultdict(int)

        for card in self.all_cards():
            vp = card.get_victory_points(self)
            if vp != 0 or card.is_victory or card.name == "Curse":
                counts[card.name] += 1
                points[card.name] += vp

        if self.vp_tokens:
            points["VP Tokens"] += self.vp_tokens

        if self.misery:
            label = "Miserable" if self.misery == 1 else "Twice Miserable"
            points[label] -= 2 * self.misery
            counts[label] = 1

        breakdown = {name: {"count": counts.get(name, 0), "vp": vp} for name, vp in points.items()}
        return breakdown


if TYPE_CHECKING:
    # Only imported for type checking to avoid runtime circular imports
    from dominion.ai.base_ai import AI

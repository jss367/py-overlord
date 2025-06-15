import random
from dataclasses import dataclass, field

from dominion.cards.base_card import Card
from dominion.cards.registry import get_card


@dataclass
class PlayerState:
    ai: "AI"  # Type annotation as string to avoid circular import

    # Resources
    actions: int = 1
    buys: int = 1
    coins: int = 0
    potions: int = 0

    # Card collections
    hand: list[Card] = field(default_factory=list)
    deck: list[Card] = field(default_factory=list)
    discard: list[Card] = field(default_factory=list)
    in_play: list[Card] = field(default_factory=list)
    duration: list[Card] = field(default_factory=list)
    multiplied_durations: list[Card] = field(default_factory=list)

    # Misc counters
    vp_tokens: int = 0
    miser_coppers: int = 0
    ignore_action_bonuses: bool = False
    collection_played: int = 0

    # Turn tracking
    turns_taken: int = 0
    actions_played: int = 0
    actions_this_turn: int = 0
    bought_this_turn: list[str] = field(default_factory=list)

    def initialize(self, use_shelters: bool = False):
        """Set up starting deck and draw initial hand.

        If ``use_shelters`` is ``True``, start with Necropolis, Hovel and
        Overgrown Estate instead of three Estates as in the Dark Ages expansion.
        """

        # Create starting deck
        self.deck = [get_card("Copper") for _ in range(7)]
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

        # Reset resources
        self.actions = 1
        self.buys = 1
        self.coins = 0
        self.potions = 0
        self.vp_tokens = 0
        self.miser_coppers = 0
        self.ignore_action_bonuses = False
        self.collection_played = 0
        self.turns_taken = 0
        self.actions_played = 0
        self.actions_this_turn = 0
        self.bought_this_turn = []

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
        """Shuffle discard pile to create new deck."""
        self.deck = self.discard[:]
        random.shuffle(self.deck)
        self.discard = []

    def count_in_deck(self, card_name: str) -> int:
        """Count total copies of named card across all piles."""
        return sum(
            1
            for card in (self.hand + self.deck + self.discard + self.in_play + self.duration)
            if card.name == card_name
        )

    # Alias used by strategy condition evaluation
    def count(self, card_name: str) -> int:
        return self.count_in_deck(card_name)

    def get_victory_points(self, game_state) -> int:
        """Calculate total victory points."""
        return (
            sum(
                card.get_victory_points(self)
                for card in (
                    self.hand + self.deck + self.discard + self.in_play + self.duration
                )
            )
            + self.vp_tokens
        )

    def all_cards(self) -> list[Card]:
        """Return a list of all cards the player possesses."""
        return self.hand + self.deck + self.discard + self.in_play + self.duration

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

        breakdown = {name: {"count": counts.get(name, 0), "vp": vp} for name, vp in points.items()}
        return breakdown

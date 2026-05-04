from abc import ABC, abstractmethod
from typing import Optional

from dominion.cards.base_card import Card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState


class AI(ABC):
    """Base class for all AIs."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def choose_action(self, state: GameState, choices: list[Optional[Card]]) -> Optional[Card]:
        """Choose an action to play from available choices."""
        pass

    @abstractmethod
    def choose_treasure(self, state: GameState, choices: list[Optional[Card]]) -> Optional[Card]:
        """Choose a treasure to play from available choices."""
        pass

    @abstractmethod
    def choose_buy(self, state: GameState, choices: list[Optional[Card]]) -> Optional[Card]:
        """Choose a card to buy from available choices."""
        pass

    @abstractmethod
    def choose_card_to_trash(self, state: GameState, choices: list[Card]) -> Optional[Card]:
        """Choose a card to trash from available choices."""
        pass

    def choose_charm_option(self, state: GameState, player: PlayerState, options: list[str]) -> str:
        """Select which of Charm's modes to use when played."""

        if "gain" in options:
            return "gain"
        if "coins" in options:
            return "coins"
        return options[0] if options else "coins"

    def should_trash_engineer_for_extra_gains(
        self, state: GameState, player: PlayerState, engineer: Card
    ) -> bool:
        """Decide whether to trash Engineer to gain two additional cards.

        The default behaviour is conservative and keeps the Engineer in play,
        ensuring existing AIs retain their previous behaviour unless they
        explicitly opt in to the extra gains.
        """

        return False

    def should_reveal_moat(self, state: GameState, player: PlayerState) -> bool:
        """Decide whether to reveal Moat in response to an attack."""

        return True

    def should_play_vassal_action(
        self, state: GameState, player: PlayerState, card: Card
    ) -> bool:
        """Decide whether to play the Action card revealed/discarded by Vassal.

        The default is to always play it — Vassal's bonus play is strictly
        free value (it doesn't consume an action) so there's no reason to
        skip a free Action. Strategies may override (e.g. to avoid playing
        a junk Action card like Necropolis).
        """
        return True

    def should_chancellor_discard_deck(
        self, state: GameState, player: PlayerState
    ) -> bool:
        """Decide whether to put the deck into the discard pile via Chancellor.

        Default: discard the deck whenever it's reasonably large. The trigger
        of 5+ cards captures the case where reshuffling is genuinely useful.
        """
        return len(player.deck) >= 5

    def should_trash_copper_for_moneylender(
        self, state: GameState, player: PlayerState
    ) -> bool:
        """Decide whether to trash a Copper for +$3 with Moneylender.

        Default: always trash, since +$3 is strictly better than +$1 from
        the Copper itself, and trashing a Copper thins the deck.
        """
        return True

    def choose_treasure_to_trash_with_bandit(
        self,
        state: GameState,
        attacker: PlayerState,
        target: PlayerState,
        treasures: list[Card],
    ) -> Card:
        """Pick which Treasure (other than Copper) the target trashes for Bandit.

        Default: trash the most valuable revealed Treasure (e.g. Gold > Silver).
        """
        return max(treasures, key=lambda c: (c.cost.coins, c.name))

    def choose_treasure_to_trash_with_thief(
        self,
        state: GameState,
        attacker: PlayerState,
        target: PlayerState,
        treasures: list[Card],
    ) -> Card:
        """Pick which Treasure the target trashes for Thief.

        Default: trash the most valuable revealed Treasure.
        """
        return max(treasures, key=lambda c: (c.cost.coins, c.name))

    def should_gain_thief_treasure(
        self, state: GameState, player: PlayerState, card: Card
    ) -> bool:
        """Decide whether to keep a Treasure trashed by Thief.

        Default: keep anything more valuable than Copper.
        """
        return card.name != "Copper"

    def choose_topdeck_or_discard(
        self,
        state: GameState,
        chooser: PlayerState,
        target: PlayerState,
        revealed: Card,
        *,
        is_self: bool,
    ) -> bool:
        """Decide whether the revealed top card should be discarded.

        Used by Spy: ``chooser`` decides whether ``target`` discards their
        revealed top card or puts it back. Returns True to discard,
        False to topdeck.

        Default heuristic:
          - If the revealed card is junk (Curse, cheap Victory, Copper) and
            the target is the chooser themselves → discard it (drawing fresh).
          - If the target is an opponent → discard valuable cards (Action,
            Treasure of cost 3+) and keep their junk on top.
        """

        is_junk = (
            revealed.name == "Curse"
            or (revealed.is_victory and not revealed.is_action and revealed.cost.coins <= 2)
            or revealed.name == "Copper"
        )

        if is_self:
            return is_junk
        # Target is opponent: discard if not junk (waste their next draw).
        return not is_junk

    def should_play_guard_dog(
        self, state: GameState, player: PlayerState, card: Card
    ) -> bool:
        """Decide whether to play Guard Dog in response to an attack."""

        return True

    def should_reveal_gold_for_legionary(
        self, state: GameState, player: PlayerState
    ) -> bool:
        """Decide whether to reveal a Gold when playing Legionary."""

        return any(card.name == "Gold" for card in player.hand)

    def choose_gladiator_reveal_target(
        self, state: GameState, player: PlayerState
    ) -> Optional[Card]:
        """Select which card to reveal when playing Gladiator."""

        if not player.hand:
            return None

        return max(
            player.hand,
            key=lambda card: (card.cost.coins, card.stats.coins, card.name),
        )

    def should_reveal_matching_gladiator(
        self,
        state: GameState,
        player: PlayerState,
        card_name: str,
        opponent: PlayerState,
    ) -> bool:
        """Decide whether to reveal a matching card during a Gladiator duel."""

        return True

    def should_keep_library_action(self, state: GameState, player: PlayerState, card: Card) -> bool:
        """Decide whether to keep a drawn Action card while resolving Library."""

        return player.actions > 0

    def choose_cards_to_trash(self, state: GameState, choices: list[Card], count: int) -> list[Card]:
        """Select up to ``count`` cards to trash, defaulting to single picks."""

        remaining = list(choices)
        selected: list[Card] = []

        while remaining and len(selected) < count:
            choice = self.choose_card_to_trash(state, remaining)
            if choice is None or choice not in remaining:
                break
            selected.append(choice)
            remaining.remove(choice)

        return selected

    def choose_black_market_purchase(
        self, state: GameState, player: PlayerState, choices: list[Card]
    ) -> Optional[Card]:
        """Select a card to buy from the Black Market reveal, if any."""

        affordable = [
            card
            for card in choices
            if card.cost.potions <= player.potions
            and card.cost.coins <= player.coins + player.coin_tokens
        ]
        if not affordable:
            return None
        return max(affordable, key=lambda card: (card.cost.coins, card.name))

    def order_cards_for_black_market_bottom(
        self, state: GameState, player: PlayerState, cards: list[Card]
    ) -> list[Card]:
        """Return the order to return unbought Black Market cards."""

        return list(cards)

    def choose_envoy_discard(
        self, state: GameState, chooser: PlayerState, target: PlayerState, revealed: list[Card]
    ) -> Optional[Card]:
        """Select which card the next player should discard from Envoy."""

        if not revealed:
            return None
        return max(revealed, key=lambda card: (card.cost.coins, card.stats.cards, card.name))

    def choose_governor_option(
        self, state: GameState, player: PlayerState, options: list[str]
    ) -> str:
        """Choose which Governor mode to use."""

        if "upgrade" in options and any(card.name == "Curse" for card in player.hand):
            return "upgrade"
        if "gold" in options and state.supply.get("Gold", 0) > 0:
            return "gold"
        return options[0] if options else "cards"

    def choose_wild_hunt_option(
        self, state: GameState, player: PlayerState, options: list[str]
    ) -> str:
        """Select which Wild Hunt mode to use when played."""

        if "draw" in options:
            return "draw"
        return options[0] if options else "draw"

    def choose_farmers_market_option(
        self,
        state: GameState,
        player: PlayerState,
        options: list[str],
        pile_tokens: int,
    ) -> str:
        """Choose which Farmers' Market mode to use when played."""

        if not options:
            return "coins"

        if "coins" not in options:
            return options[0]

        if pile_tokens <= 0:
            return "coins"

        if "vp" in options and pile_tokens >= 4:
            return "vp"

        return "coins"

    def choose_prince_target(
        self, state: GameState, player: PlayerState, choices: list[Optional[Card]]
    ) -> Optional[Card]:
        """Select which Action to set aside with Prince."""

        actual_choices = [card for card in choices if card]
        if not actual_choices:
            return None
        return min(actual_choices, key=lambda card: (card.cost.coins, card.name))

    def should_play_avanto_from_sauna(self, state: GameState, player: PlayerState) -> bool:
        """Decide whether to continue the Sauna/Avanto chain from Sauna."""

        return True

    def should_play_sauna_from_avanto(self, state: GameState, player: PlayerState) -> bool:
        """Decide whether to continue the Sauna/Avanto chain from Avanto."""

        return True

    def choose_cards_to_set_aside_for_church(
        self, state: GameState, player: PlayerState, choices: list[Card], max_count: int
    ) -> list[Card]:
        """Choose which cards to set aside when playing Church."""

        if max_count <= 0:
            return []
        ordered = sorted(
            choices, key=lambda card: (card.is_action, card.cost.coins, card.name)
        )
        return ordered[:max_count]

    def choose_church_trash(
        self, state: GameState, player: PlayerState
    ) -> Optional[Card]:
        """Choose which card to trash after resolving Church."""

        priorities = ["Curse", "Estate", "Hovel", "Overgrown Estate", "Copper"]
        for name in priorities:
            for card in player.hand:
                if card.name == name:
                    return card
        return None

    def choose_archive_card(
        self, state: GameState, player: PlayerState, choices: list[Card]
    ) -> Optional[Card]:
        """Select which set-aside Archive card to add to hand at the start of turn."""

        if not choices:
            return None

        return choices[0]

    def choose_cards_to_discard(
        self,
        state: GameState,
        player: PlayerState,
        choices: list[Card],
        count: int,
        *,
        reason: Optional[str] = None,
    ) -> list[Card]:
        """Choose up to ``count`` cards to discard from ``choices``.

        Default heuristic prefers to discard obviously low-value cards:
        Curses, low-cost non-action Victory, then Copper, then by cost.

        ``reason`` can be used by subclasses to tailor decisions (e.g. "torturer").
        """

        def discard_priority(card: Card) -> tuple[int, int, str]:
            if card.name == "Curse":
                return (0, 0, card.name)
            # Non-action green cards are typically dead in hand; prefer cheaper ones first
            if card.is_victory and not card.is_action and card.cost.coins <= 2:
                return (1, card.cost.coins, card.name)
            if card.name == "Copper":
                return (2, 0, card.name)
            # Otherwise rank by coin cost (cheaper first)
            return (3, card.cost.coins, card.name)

        available = list(choices)
        ordered = sorted(available, key=discard_priority)
        return ordered[: max(0, min(count, len(ordered)))]

    def choose_card_to_delay(
        self, state: GameState, player: PlayerState, choices: list[Card]
    ) -> Optional[Card]:
        """Select a card to set aside for effects like Puzzle Box or Delay.

        The default behaviour mirrors previous heuristics by preferring to set
        aside an Action card if possible and otherwise opting out.
        """

        if not choices:
            return None

        action_choices = [card for card in choices if card.is_action]
        if not action_choices:
            return None

        selection = self.choose_action(state, action_choices + [None])
        if selection in action_choices:
            return selection

        return None

    def should_reveal_trader(self, state: GameState, player: PlayerState, gained_card: Card, *, to_deck: bool) -> bool:
        """Decide whether to reveal Trader to exchange a gain for Silver."""

        return False

    def should_play_weaver_on_discard(
        self, state: GameState, player: PlayerState, card: Card
    ) -> bool:
        """Decide whether to play Weaver when it is discarded outside Clean-up."""

        return True

    def should_discard_for_vault(self, state: GameState, player: PlayerState) -> bool:
        """Decide if the player should discard two cards for Vault's reaction."""

        low_value = [
            card
            for card in player.hand
            if card.name == "Copper"
            or card.name == "Curse"
            or (card.is_victory and not card.is_action and card.cost.coins <= 2)
        ]
        return len(low_value) >= 2

    def choose_watchtower_reaction(
        self, state: GameState, player: PlayerState, gained_card: Card
    ) -> Optional[str]:
        """Return 'trash', 'topdeck', or ``None`` when revealing Watchtower."""

        if gained_card.name == "Curse":
            return "trash"
        return None

    def should_topdeck_with_royal_seal(
        self, state: GameState, player: PlayerState, gained_card: Card
    ) -> bool:
        """Decide whether to topdeck a gain thanks to Royal Seal."""

        return False


    def should_discard_deck_with_messenger(
        self, state: GameState, player: PlayerState
    ) -> bool:
        """Decide whether to discard the deck when playing Messenger."""

    def should_topdeck_with_insignia(
        self, state: GameState, player: PlayerState, gained_card: Card
    ) -> bool:
        """Decide whether to topdeck a card gained while Insignia is active."""


        return False

    def order_cards_for_topdeck(
        self, state: GameState, player: PlayerState, cards: list[Card]
    ) -> list[Card]:
        """Return cards in the order they should be placed back on the deck."""

        return list(cards)

    def should_react_with_market_square(
        self, state: GameState, player: PlayerState, trashed_card: Card
    ) -> bool:
        """Decide whether to discard Market Square to gain a Gold."""

        return True

    def choose_hunting_grounds_reward(
        self, state: GameState, player: PlayerState
    ) -> str:
        """Choose between gaining a Duchy or three Estates when Hunting Grounds is trashed."""

        if state.supply.get("Duchy", 0) > 0:
            return "duchy"
        return "estates"

    def choose_way(self, state: GameState, card: Card, ways: list) -> Optional[object]:
        """Choose a Way to use when playing a card. Default is none."""
        return None

    def should_spend_favor_on_cave_dwellers(
        self, state: GameState, player: PlayerState
    ) -> bool:
        """Decide whether to spend a Favor on Cave Dwellers' discard-then-draw.

        Default: spend whenever the hand contains a junk card (Curse, Copper,
        cheap Victory, Estate, or any non-Action Victory).
        """
        for card in player.hand:
            if card.name in {"Curse", "Copper", "Estate", "Hovel", "Overgrown Estate"}:
                return True
            if card.is_victory and not card.is_action and card.cost.coins <= 2:
                return True
        return False

    def choose_card_to_discard_for_cave_dwellers(
        self, state: GameState, player: PlayerState, choices: list[Card]
    ) -> Optional[Card]:
        """Pick a card to discard when activating Cave Dwellers."""
        if not choices:
            return None
        picked = self.choose_cards_to_discard(state, player, choices, 1, reason="cave_dwellers")
        return picked[0] if picked else None

    def choose_card_to_topdeck_from_hand(
        self, state: GameState, player: PlayerState, choices: list[Card], reason: Optional[str] = None
    ) -> Optional[Card]:
        """Choose which card from hand to put on top of deck (Pilgrim, etc.).

        Default: prefer to top-deck the most valuable Action so it's drawn
        next turn, otherwise the cheapest junk.
        """
        if not choices:
            return None

        actions = [c for c in choices if c.is_action]
        if actions:
            return max(actions, key=lambda c: (c.cost.coins, c.is_duration, c.name))

        treasures = [c for c in choices if c.is_treasure]
        if treasures:
            return max(treasures, key=lambda c: (c.cost.coins, c.name))

        return min(choices, key=lambda c: (c.cost.coins, c.name))

    def choose_action_to_trash_from_supply(
        self, state: GameState, player: PlayerState, choices: list[Card]
    ) -> Optional[Card]:
        """Lurker mode 1: pick an Action card in supply to trash.

        Default heuristic: prioritise cards that drain meaningful piles —
        the top of a split pile (Settlers exposes Bustling Village; Student
        drains the Wizards pile toward Lich). Ties broken by lowest cost so
        we don't spend value trashing premium cards.
        """
        if not choices:
            return None

        priority_pile_drainers = {"Settlers", "Student", "Conjurer", "Sorcerer"}
        for name in ("Student", "Conjurer", "Sorcerer", "Settlers"):
            for c in choices:
                if c.name == name:
                    return c
        # Otherwise prefer the cheapest Action so we don't waste a high-value pile.
        return min(choices, key=lambda c: (c.cost.coins, c.name))

    def choose_action_to_gain_from_trash(
        self, state: GameState, player: PlayerState, choices: list[Card]
    ) -> Optional[Card]:
        """Lurker mode 2: pick an Action in the trash to gain."""
        if not choices:
            return None
        return max(choices, key=lambda c: (c.cost.coins, c.name))

    def choose_lurker_mode(
        self, state: GameState, player: PlayerState, can_trash: bool, can_gain: bool
    ) -> str:
        """Return 'trash' or 'gain' for Lurker. Default: gain if any Action sits in trash, else trash."""
        if can_gain:
            return "gain"
        return "trash"

    def choose_continue_target(
        self, state: GameState, player: PlayerState, choices: list[Card]
    ) -> Optional[Card]:
        """Pick which $0-$4 card to gain and play via the Continue event."""
        if not choices:
            return None
        actions = [c for c in choices if c.is_action]
        if actions:
            return max(actions, key=lambda c: (c.cost.coins, c.stats.cards, c.stats.actions, c.name))
        return max(choices, key=lambda c: (c.cost.coins, c.name))

    def choose_card_to_gain_from_trash(
        self, state: GameState, player: PlayerState, choices: list[Card], max_cost: int
    ) -> Optional[Card]:
        """Used by Lich's "+ gain a cheaper Action from trash" clause."""
        if not choices:
            return None
        return max(choices, key=lambda c: (c.cost.coins, c.name))

    def use_amphora_now(self, state: GameState) -> bool:
        """Decide whether to take Amphora's bonus immediately."""
        return True

    def choose_torturer_attack(self, state: GameState, player: PlayerState) -> bool:
        """Choose whether to discard two cards or gain a Curse from Torturer.

        The default heuristic discards when at least two low-value cards are
        present (Curses, Estates, or Coppers). Otherwise, it keeps the valuable
        hand and accepts the Curse.
        """

        hand = list(player.hand)

        if len(hand) < 2:
            return False

        def is_low_value(card: Card) -> bool:
            if card.name == "Curse":
                return True
            if card.name == "Copper":
                return True
            if card.is_victory and not card.is_action and card.cost.coins <= 2:
                return True
            return False

        low_value_cards = [card for card in hand if is_low_value(card)]
        return len(low_value_cards) >= 2

    def order_cards_for_patrol(self, state: GameState, player: PlayerState, cards: list[Card]) -> list[Card]:
        """Return cards in draw priority order for Patrol's topdeck effect."""

        def priority(card: Card) -> tuple[int, int, str]:
            score = 0
            if card.is_action:
                score += 200
            if card.is_treasure:
                score += 100 + card.cost.coins
            score += card.cost.coins
            return (score, card.stats.cards, card.name)

        return sorted(cards, key=priority, reverse=True)

    def choose_treasures_to_set_aside_for_crypt(
        self, state: GameState, player: PlayerState, treasures: list[Card]
    ) -> list[Card]:
        """Select treasures to set aside when playing Crypt.

        The default behaviour is conservative: keep all treasures in hand.
        """

        return []

    def choose_treasure_to_return_from_crypt(
        self, state: GameState, player: PlayerState, treasures: list[Card]
    ) -> Optional[Card]:
        """Choose which set-aside treasure to return to hand for Crypt.

        By default this returns the most valuable treasure available.
        """

        if not treasures:
            return None

        return max(treasures, key=lambda card: (card.cost.coins, card.name))

    def choose_treasures_to_set_aside_with_trickster(
        self,
        state: GameState,
        player: PlayerState,
        treasures: list[Card],
        max_count: int,
    ) -> list[Card]:
        """Select up to ``max_count`` treasures to keep with Trickster."""

        if max_count <= 0 or not treasures:
            return []

        ordered = sorted(treasures, key=lambda card: (card.cost.coins, card.name), reverse=True)
        return ordered[:max_count]

    def choose_tragic_hero_treasure(
        self, state: GameState, player: PlayerState, treasures: list[Card]
    ) -> Optional[Card]:
        """Select which treasure to gain from Tragic Hero's trash effect.

        Defaults to taking the most expensive treasure available.
        """

        if not treasures:
            return None

        return max(treasures, key=lambda card: (card.cost.coins, card.name))

    def choose_card_to_topdeck_from_discard(
        self, state: GameState, player: PlayerState, choices: list[Card]
    ) -> Optional[Card]:
        """Choose a card from discard to put on top of deck (Harbinger)."""
        if not choices:
            return None
        return max(choices, key=lambda card: (card.cost.coins, card.name))

    def choose_graverobber_mode(
        self, state: GameState, player: PlayerState, options: list[str]
    ) -> str:
        """Choose Graverobber mode: 'gain_from_trash' or 'upgrade'."""
        if "gain_from_trash" in options:
            return "gain_from_trash"
        return options[0] if options else "upgrade"

    def should_joust_province(self, state: GameState, player: PlayerState) -> bool:
        """Decide whether to set aside Province for Joust."""
        return True

    def should_set_aside_cargo_ship(
        self, state: GameState, player: PlayerState, gained_card: Card
    ) -> bool:
        """Decide whether to set aside a gained card with Cargo Ship."""
        return gained_card.cost.coins >= 3

    def should_topdeck_treasury(self, state: GameState, player: PlayerState) -> bool:
        """Decide whether to topdeck Treasury at end of buy phase."""
        return True

    # --- Seaside hooks -------------------------------------------------

    def choose_card_to_set_aside_for_haven(
        self, state: GameState, player: PlayerState, choices: list[Card]
    ) -> Optional[Card]:
        """Pick a card to set aside under Haven for next turn.

        Default: prefer the most valuable Action; otherwise the most expensive
        Treasure. Skip if the only options are clear junk.
        """
        if not choices:
            return None

        actions = [c for c in choices if c.is_action]
        if actions:
            return max(actions, key=lambda c: (c.cost.coins, c.stats.cards, c.name))

        treasures = [c for c in choices if c.is_treasure and c.name != "Copper"]
        if treasures:
            return max(treasures, key=lambda c: (c.cost.coins, c.name))

        return None

    def choose_card_to_ambassador(
        self, state: GameState, player: PlayerState, choices: list[Card]
    ) -> Optional[Card]:
        """Pick a card to "reveal" with Ambassador (and return copies of)."""
        if not choices:
            return None

        # Prefer to recycle the worst card we have copies of.
        priorities = ["Curse", "Estate", "Hovel", "Overgrown Estate", "Copper"]
        for name in priorities:
            for c in choices:
                if c.name == name:
                    return c
        return None

    def choose_pile_to_embargo(
        self, state: GameState, player: PlayerState
    ) -> Optional[str]:
        """Choose which Supply pile to place an Embargo token on.

        Default: embargo Province if available; otherwise the most expensive
        Action / Victory in the Supply.
        """
        from ..cards.registry import get_card

        if state.supply.get("Province", 0) > 0:
            return "Province"

        candidates = []
        for name, count in state.supply.items():
            if count <= 0:
                continue
            if name in {"Curse", "Copper"}:
                continue
            try:
                card = get_card(name)
            except ValueError:
                continue
            candidates.append((card.cost.coins, name))

        if not candidates:
            return None
        candidates.sort(reverse=True)
        return candidates[0][1]

    def choose_smugglers_target(
        self, state: GameState, player: PlayerState, choices: list[Card]
    ) -> Optional[Card]:
        """Pick the most valuable card to smuggle (default: highest cost)."""
        if not choices:
            return None
        return max(choices, key=lambda c: (c.cost.coins, c.is_action, c.name))

    def choose_card_to_set_aside_for_island(
        self, state: GameState, player: PlayerState, choices: list[Card]
    ) -> Optional[Card]:
        """Pick a card from hand to send to the Island mat with Island."""
        if not choices:
            return None

        # Prefer to exile junk (Curse > non-Action Victory > Copper).
        priorities = ["Curse", "Estate", "Hovel", "Overgrown Estate", "Copper"]
        for name in priorities:
            for c in choices:
                if c.name == name:
                    return c

        # Otherwise put away a non-action victory card if any.
        greens = [c for c in choices if c.is_victory and not c.is_action]
        if greens:
            return min(greens, key=lambda c: (c.cost.coins, c.name))

        return None

    def choose_pirate_ship_mode(
        self, state: GameState, player: PlayerState, tokens: int
    ) -> str:
        """Decide between attacking and cashing in Pirate Ship tokens."""
        if tokens >= 3:
            return "coins"
        return "attack"

    def choose_treasure_to_trash_with_pirate_ship(
        self,
        state: GameState,
        player: PlayerState,
        target: PlayerState,
        treasures: list[Card],
    ) -> Optional[Card]:
        """Pick which revealed Treasure to trash from the target."""
        if not treasures:
            return None
        return max(treasures, key=lambda c: (c.cost.coins, c.name))

    def choose_card_to_gain_with_blockade(
        self, state: GameState, player: PlayerState, max_cost: int
    ) -> Optional[Card]:
        """Pick a Supply card costing up to ``max_cost`` to gain with Blockade."""
        from ..cards.registry import get_card

        candidates = []
        for name, count in state.supply.items():
            if count <= 0:
                continue
            try:
                card = get_card(name)
            except ValueError:
                continue
            if card.cost.coins > max_cost:
                continue
            if card.cost.potions > 0 or card.cost.debt > 0:
                continue
            if card.name == "Curse":
                continue
            candidates.append(card)

        if not candidates:
            return None
        return max(candidates, key=lambda c: (c.cost.coins, c.is_action, c.name))

    def should_play_gain_with_sailor(
        self, state: GameState, player: PlayerState, gained_card: Card
    ) -> bool:
        """Decide whether to play a freshly gained Duration card via Sailor.

        Sailor only triggers on Duration gains; this hook just lets a player
        opt out (e.g. if they don't want to dirty in-play with the card).
        Default: always play it, matching the printed-card mandate.
        """
        return True

    def choose_sailor_trash(
        self, state: GameState, player: PlayerState, choices: list[Card]
    ) -> Optional[Card]:
        """Pick a card to optionally trash at the start of Sailor's next turn."""
        priorities = ["Curse", "Estate", "Hovel", "Overgrown Estate", "Copper"]
        for name in priorities:
            for c in choices:
                if c.name == name:
                    return c
        return None

    # ------------------------------------------------------------------
    # Rising Sun decision hooks
    # ------------------------------------------------------------------

    def should_take_gold_mine_gold(
        self, state: GameState, player: PlayerState
    ) -> bool:
        """Decide whether Gold Mine should gain a Gold (taking 4 Debt).

        Default: take the Gold whenever the player can pay off the Debt
        within a turn or two — i.e. the deck regularly produces $4+ — but
        skip when already burdened by Debt.
        """
        if state.supply.get("Gold", 0) <= 0:
            return False
        if player.debt > 0:
            return False
        return True

    def choose_kitsune_options(
        self,
        state: GameState,
        player: PlayerState,
        options: list[str],
    ) -> list[str]:
        """Pick two of Kitsune's four options.

        Default heuristic: prefer cursing opponents, then +$2, then +1
        Action, falling back to gaining a Silver.
        """
        priority = ["curse", "coins", "action", "silver"]
        ordered = [opt for opt in priority if opt in options]
        return ordered[:2]

    def should_rustic_village_discard(
        self, state: GameState, player: PlayerState
    ) -> bool:
        """Decide whether Rustic Village should discard 2 for +1 Card.

        Default: discard when there are at least two clearly low-value cards
        in hand (Curse, Copper, cheap Victory).
        """
        low_value = 0
        for card in player.hand:
            if card.name in {"Curse", "Copper", "Estate", "Hovel", "Overgrown Estate"}:
                low_value += 1
            elif card.is_victory and not card.is_action and card.cost.coins <= 2:
                low_value += 1
        return low_value >= 2

    def should_reveal_snake_witch(
        self, state: GameState, player: PlayerState
    ) -> bool:
        """Decide whether to reveal Snake Witch's hand to curse opponents.

        Default: reveal whenever doing so would actually curse someone (the
        Curse pile isn't empty) — handing back Snake Witch to its pile is a
        small loss in exchange for distributing Curses.
        """
        if state.supply.get("Curse", 0) <= 0:
            return False
        return any(other is not player for other in state.players)

    def choose_asceticism_overpay(
        self, state: GameState, player: PlayerState, available: int
    ) -> int:
        """Choose how much extra coin to pay on top of Asceticism's $2.

        Default: trash low-value cards (Curse, Copper, cheap Victory) only,
        capped by available coins and hand size.
        """
        cheap = [
            card
            for card in player.hand
            if card.name in {"Curse", "Copper", "Estate", "Hovel", "Overgrown Estate"}
            or (card.is_victory and not card.is_action and card.cost.coins <= 2)
        ]
        return min(len(cheap), available)

    def choose_sickness_mode(
        self, state: GameState, player: PlayerState
    ) -> str:
        """Pick Sickness's mode at end of turn: 'curse' or 'discard'.

        Default: discard 3 if the hand contains 3+ junk cards (Curses,
        Coppers, cheap Victory cards), otherwise take the Curse onto your
        deck.
        """
        junk = sum(
            1
            for card in player.hand
            if card.name in {"Curse", "Copper", "Estate"}
            or (card.is_victory and not card.is_action and card.cost.coins <= 2)
        )
        if junk >= 3:
            return "discard"
        return "curse"

    def choose_riverboat_set_aside(
        self, state: GameState, player: PlayerState, candidates: list[Card]
    ) -> "Card | None":
        """Pick which $5 non-Duration Action card Riverboat sets aside.

        Default: prefer cards that produce extra cards/actions and survive
        being played repeatedly across turns. Falls back to the first
        candidate.
        """
        if not candidates:
            return None
        return max(
            candidates,
            key=lambda c: (
                c.stats.cards * 2 + c.stats.actions + c.stats.coins,
                c.name,
            ),
        )

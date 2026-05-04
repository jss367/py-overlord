from dataclasses import dataclass
from enum import Enum


@dataclass
class CardCost:
    coins: int = 0
    potions: int = 0
    debt: int = 0

    def comparison_tuple(self) -> tuple[int, int, int]:
        """Return a tuple representation for comparing card costs."""
        return (self.coins, self.potions, self.debt)


@dataclass
class CardStats:
    actions: int = 0
    cards: int = 0
    coins: int = 0
    buys: int = 0
    vp: int = 0
    potions: int = 0


class CardType(Enum):
    ACTION = "action"
    TREASURE = "treasure"
    VICTORY = "victory"
    CURSE = "curse"
    ATTACK = "attack"
    REACTION = "reaction"
    DURATION = "duration"
    COMMAND = "command"
    SHADOW = "shadow"
    OMEN = "omen"
    RUINS = "ruins"
    KNIGHT = "knight"
    LOOTER = "looter"
    CASTLE = "castle"
    NIGHT = "night"
    SPIRIT = "spirit"
    HEIRLOOM = "heirloom"
    FATE = "fate"
    DOOM = "doom"
    ZOMBIE = "zombie"
    LIAISON = "liaison"
    RESERVE = "reserve"
    TRAVELLER = "traveller"


class Card:
    def __init__(self, name: str, cost: CardCost, stats: CardStats, types: list[CardType]):
        self.name = name
        self.cost = cost
        self.stats = stats
        self.types = types
        self.duration_persistent = False
        # Nocturne: heirloom name (subclasses set this); when this card is in
        # the kingdom one starting Copper is replaced with this Heirloom.
        if not hasattr(self, "heirloom"):
            self.heirloom: str | None = None

        # Debug validation
        if not isinstance(types, list):
            raise ValueError(f"Card {name} initialized with types that's not a list: {types}")
        for t in types:
            if not isinstance(t, CardType):
                raise ValueError(f"Card {name} initialized with invalid type: {t}")

    @property
    def is_action(self) -> bool:
        return CardType.ACTION in self.types

    @property
    def is_treasure(self) -> bool:
        return CardType.TREASURE in self.types

    @property
    def is_victory(self) -> bool:
        return CardType.VICTORY in self.types

    @property
    def is_attack(self) -> bool:
        return CardType.ATTACK in self.types

    @property
    def is_reaction(self) -> bool:
        return CardType.REACTION in self.types

    @property
    def is_duration(self) -> bool:
        return CardType.DURATION in self.types

    @property
    def is_command(self) -> bool:
        return CardType.COMMAND in self.types

    @property
    def is_shadow(self) -> bool:
        return CardType.SHADOW in self.types

    @property
    def is_omen(self) -> bool:
        return CardType.OMEN in self.types

    @property
    def is_ruins(self) -> bool:
        return CardType.RUINS in self.types

    @property
    def is_knight(self) -> bool:
        return CardType.KNIGHT in self.types

    @property
    def is_looter(self) -> bool:
        return CardType.LOOTER in self.types

    @property
    def is_castle(self) -> bool:
        return CardType.CASTLE in self.types

    @property
    def is_night(self) -> bool:
        return CardType.NIGHT in self.types

    @property
    def is_spirit(self) -> bool:
        return CardType.SPIRIT in self.types

    @property
    def is_fate(self) -> bool:
        return CardType.FATE in self.types

    @property
    def is_doom(self) -> bool:
        return CardType.DOOM in self.types

    @property
    def is_zombie(self) -> bool:
        return CardType.ZOMBIE in self.types

    @property
    def is_heirloom(self) -> bool:
        return CardType.HEIRLOOM in self.types
    def is_reserve(self) -> bool:
        return CardType.RESERVE in self.types

    @property
    def is_traveller(self) -> bool:
        return CardType.TRAVELLER in self.types

    @property
    def is_liaison(self) -> bool:
        return CardType.LIAISON in self.types

    def get_victory_points(self, player) -> int:
        """Get victory points this card provides for the given player."""
        return self.stats.vp

    def starting_supply(self, game_state) -> int:
        """Get number of copies of this card in the supply at game start."""
        return 10

    def may_be_bought(self, game_state) -> bool:
        """Check if this card can currently be bought."""
        return True

    def on_play(self, game_state):
        """Execute this card's effects when played."""
        player = game_state.current_player

        # Rising Sun: "+1 Sun" always appears first on Omens, before any
        # other text. Removing the last Sun token activates the Prophecy in
        # the middle of resolving the Omen (e.g. so Kitsune sees the new
        # rule before its own choices apply).
        if self.is_omen:
            game_state.remove_sun_token(1)

        if player.ignore_action_bonuses:
            added_actions = 0
        else:
            added_actions = self.stats.actions
        player.actions += added_actions
        player.coins += self.stats.coins
        player.potions += self.stats.potions
        player.buys += self.stats.buys

        if self.stats.cards > 0:
            game_state.draw_cards(player, self.stats.cards)

        # Let subclasses add additional effects
        self.play_effect(game_state)

        # Dark Ages — Urchin reacts to any Attack played while it is in
        # play, including Attacks played indirectly via Throne Room,
        # King's Court, Procession, Band of Misfits, etc. We trigger this
        # at the end of on_play so every Attack play (no matter how it was
        # initiated) is observed exactly once.
        if self.is_attack and self.name != "Urchin":
            urchins = [
                c for c in list(player.in_play)
                if c.name == "Urchin" and c is not self
            ]
            for urchin in urchins:
                react = getattr(urchin, "react_to_attack_played", None)
                if react is None:
                    continue
                try:
                    react(game_state, player, self)
                except AttributeError:
                    pass

    def play_effect(self, game_state):
        """Additional effects when card is played. Override in subclasses."""
        pass

    def on_duration(self, game_state):
        """Handle duration effects that occur at the start of the next turn.
        Override in duration card subclasses."""
        pass

    def on_buy(self, game_state):
        """Effects that happen when card is bought. Override in subclasses."""
        pass

    def may_overpay(self, game_state) -> bool:
        """Whether this card supports the Guilds Overpay mechanic when bought.

        Default False. Override on cards that allow overpay (Doctor, Herald,
        Masterpiece, Stonemason).
        """
        return False

    def on_overpay(self, game_state, player, amount: int) -> None:
        """Effects when this card is bought with overpay. Override in subclasses."""
        pass

    def on_gain(self, game_state, player):
        """Effects that happen when card is gained."""
        if self.is_action and getattr(player, "collection_played", 0) > 0:
            player.vp_tokens += player.collection_played
        if self.cost.coins == 5:
            player.gained_five_this_turn = True

    def on_trash(self, game_state, player):
        """Effects that happen when card is trashed. Override in subclasses."""
        pass

    # Adventures: Travellers expose ``next_traveller`` (a card name) to be
    # exchanged into when the card is discarded from play. Default ``None`` so
    # non-Traveller cards never trigger exchange logic.
    next_traveller: "str | None" = None

    def on_call_from_tavern(
        self, game_state, player, trigger: str, *args, **kwargs
    ) -> bool:
        """Optional hook for Reserve cards on the Tavern mat.

        Called by the engine on each known trigger ("start_of_turn",
        "action_played", "buy", "gain", "cleanup_start"). Subclasses should
        return True if they actually called this card off the mat (the engine
        will then move the card from ``tavern_mat`` to ``discard``).
        """
        return False

    def react_to_attack(self, game_state, player, attacker, attack_card) -> bool:
        """React to an incoming attack from another player.

        Override in Reaction cards to optionally block the attack. Return
        True if the attack should be considered fully blocked for this
        player (no further reactions for this attack are processed).

        The default implementation does nothing and returns False.
        """
        return False

    def get_additional_piles(self) -> dict[str, int]:
        """Return additional supply piles required by this card."""
        return {}

    def get_additional_non_supply_piles(self) -> dict[str, int]:
        """Return additional non-Supply piles required by this card.

        These piles live alongside the Supply (so cards can be looked up and
        gained from them via ``state.supply``) but they must NOT count toward
        the three-empty-piles game-end condition. Examples: Tournament Prize
        piles, Madman, Mercenary, Spirits, Wishes, Bats, Zombies, Horses,
        Spoils. Currently used by Tournament; older callers still register
        their non-Supply piles directly in ``state.supply`` without flagging
        them, which is a known limitation tracked separately.
        """
        return {}

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"Card({self.name})"

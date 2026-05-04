"""Castles 8-pile from Empires.

The Castles pile contains 8 distinct Castle cards stacked in a fixed order.
Only the top of the pile (the next un-empty Castle in order) may be bought
or gained. In a 2-player game there is 1 of each Castle; in a 3+ player
game there are 2 of each.

Each Castle is registered as its own supply pile in ``game_state.supply``;
``may_be_bought`` enforces the only-top-of-pile constraint.
"""

from ..base_card import Card, CardCost, CardStats, CardType


CASTLE_ORDER: list[str] = [
    "Humble Castle",
    "Crumbling Castle",
    "Small Castle",
    "Haunted Castle",
    "Opulent Castle",
    "Sprawling Castle",
    "Grand Castle",
    "King's Castle",
]


class _CastleBase(Card):
    """Base for the 8 Castle cards.

    All Castles share the only-top-of-pile rule and player-count-aware
    starting supply.
    """

    castle_position: int = 0  # index into CASTLE_ORDER

    def starting_supply(self, game_state) -> int:
        return 1 if len(game_state.players) <= 2 else 2

    def may_be_bought(self, game_state) -> bool:
        # Top-of-pile gating: only buyable if every earlier-order Castle is
        # fully exhausted in the supply.
        for earlier_name in CASTLE_ORDER[: self.castle_position]:
            if game_state.supply.get(earlier_name, 0) > 0:
                return False
        return super().may_be_bought(game_state)


# ---------------------------------------------------------------------------
# Individual Castle cards


class HumbleCastle(_CastleBase):
    """$3 Treasure-Victory-Castle. $1; worth 1 VP per Castle you have."""

    castle_position = 0

    def __init__(self):
        super().__init__(
            name="Humble Castle",
            cost=CardCost(coins=3),
            stats=CardStats(coins=1),
            types=[CardType.TREASURE, CardType.VICTORY, CardType.CASTLE],
        )

    def get_victory_points(self, player) -> int:
        return sum(1 for c in player.all_cards() if c.is_castle)


class CrumblingCastle(_CastleBase):
    """$4 Victory-Castle. 1 VP. On gain or trash: +1 VP token, gain a Silver."""

    castle_position = 1

    def __init__(self):
        super().__init__(
            name="Crumbling Castle",
            cost=CardCost(coins=4),
            stats=CardStats(vp=1),
            types=[CardType.VICTORY, CardType.CASTLE],
        )

    def _bonus(self, game_state, player):
        from ..registry import get_card

        player.vp_tokens += 1
        if game_state.supply.get("Silver", 0) > 0:
            game_state.supply["Silver"] -= 1
            game_state.gain_card(player, get_card("Silver"))

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)
        self._bonus(game_state, player)

    def on_trash(self, game_state, player):
        super().on_trash(game_state, player)
        self._bonus(game_state, player)


class SmallCastle(_CastleBase):
    """$5 Action-Victory-Castle. Trash this or a Castle from hand. Gain a Castle. 2 VP."""

    castle_position = 2

    def __init__(self):
        super().__init__(
            name="Small Castle",
            cost=CardCost(coins=5),
            stats=CardStats(vp=2),
            types=[CardType.ACTION, CardType.VICTORY, CardType.CASTLE],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player

        # Try trashing self from in_play first; otherwise trash a Castle from hand.
        trashed = False
        if self in player.in_play:
            player.in_play.remove(self)
            game_state.trash_card(player, self)
            trashed = True
        else:
            for card in list(player.hand):
                if card.is_castle:
                    player.hand.remove(card)
                    game_state.trash_card(player, card)
                    trashed = True
                    break

        if not trashed:
            return

        # Gain the next available Castle (top of the pile) costing up to anything.
        for name in CASTLE_ORDER:
            if game_state.supply.get(name, 0) > 0:
                castle = get_card(name)
                if not castle.may_be_bought(game_state):
                    continue
                game_state.supply[name] -= 1
                game_state.gain_card(player, castle)
                break


class HauntedCastle(_CastleBase):
    """$6 Victory-Castle. 2 VP. On gain: gain a Gold; each other player with 5+ cards
    puts 2 cards on top of their deck."""

    castle_position = 3

    def __init__(self):
        super().__init__(
            name="Haunted Castle",
            cost=CardCost(coins=6),
            stats=CardStats(vp=2),
            types=[CardType.VICTORY, CardType.CASTLE],
        )

    def on_gain(self, game_state, player):
        from ..registry import get_card

        super().on_gain(game_state, player)

        if game_state.supply.get("Gold", 0) > 0:
            game_state.supply["Gold"] -= 1
            game_state.gain_card(player, get_card("Gold"))

        for other in game_state.players:
            if other is player:
                continue
            if len(other.hand) < 5:
                continue
            # Put 2 from hand on top of deck (cheapest first).
            picks = sorted(other.hand, key=lambda c: (c.cost.coins, c.name))[:2]
            for card in picks:
                other.hand.remove(card)
                other.deck.append(card)


class OpulentCastle(_CastleBase):
    """$7 Action-Victory-Castle. Discard any number of Victory cards, +$2 each. 3 VP."""

    castle_position = 4

    def __init__(self):
        super().__init__(
            name="Opulent Castle",
            cost=CardCost(coins=7),
            stats=CardStats(vp=3),
            types=[CardType.ACTION, CardType.VICTORY, CardType.CASTLE],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        victory_cards = [c for c in player.hand if c.is_victory]
        for card in victory_cards:
            player.hand.remove(card)
            game_state.discard_card(player, card)
            player.coins += 2


class SprawlingCastle(_CastleBase):
    """$8 Victory-Castle. 4 VP. On gain: gain a Duchy or 3 Estates."""

    castle_position = 5

    def __init__(self):
        super().__init__(
            name="Sprawling Castle",
            cost=CardCost(coins=8),
            stats=CardStats(vp=4),
            types=[CardType.VICTORY, CardType.CASTLE],
        )

    def on_gain(self, game_state, player):
        from ..registry import get_card

        super().on_gain(game_state, player)

        # Prefer 3 Estates if available (5 VP > 3 VP for Duchy).
        if game_state.supply.get("Estate", 0) >= 3:
            for _ in range(3):
                game_state.supply["Estate"] -= 1
                game_state.gain_card(player, get_card("Estate"))
        elif game_state.supply.get("Duchy", 0) > 0:
            game_state.supply["Duchy"] -= 1
            game_state.gain_card(player, get_card("Duchy"))


class GrandCastle(_CastleBase):
    """$9 Victory-Castle. 5 VP. On gain: reveal hand. +1 VP token per Victory in hand or in play."""

    castle_position = 6

    def __init__(self):
        super().__init__(
            name="Grand Castle",
            cost=CardCost(coins=9),
            stats=CardStats(vp=5),
            types=[CardType.VICTORY, CardType.CASTLE],
        )

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)

        count = sum(1 for c in player.hand if c.is_victory)
        count += sum(1 for c in player.in_play if c.is_victory)
        player.vp_tokens += count


class KingsCastle(_CastleBase):
    """$10 Victory-Castle. Worth 2 VP per Castle you have."""

    castle_position = 7

    def __init__(self):
        super().__init__(
            name="King's Castle",
            cost=CardCost(coins=10),
            stats=CardStats(),
            types=[CardType.VICTORY, CardType.CASTLE],
        )

    def get_victory_points(self, player) -> int:
        return 2 * sum(1 for c in player.all_cards() if c.is_castle)


# Backwards compat alias: anywhere that imported "Castle" still gets the bottom
# Humble Castle (first in pile order). Old kingdoms / tests that reference
# "Castle" still work because we register a "Castles" alias in the registry.


Castle = HumbleCastle


__all__ = [
    "Castle",
    "HumbleCastle",
    "CrumblingCastle",
    "SmallCastle",
    "HauntedCastle",
    "OpulentCastle",
    "SprawlingCastle",
    "GrandCastle",
    "KingsCastle",
    "CASTLE_ORDER",
]

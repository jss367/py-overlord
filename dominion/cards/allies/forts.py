"""Forts split pile (Allies). Top to bottom: Tent, Garrison, Hill Fort,
Stronghold."""

from typing import ClassVar

from ..base_card import Card, CardCost, CardStats, CardType
from ._split_base import AlliesSplitCard

FORTS_PILE_ORDER = ("Tent", "Garrison", "Hill Fort", "Stronghold")


class _Forts(AlliesSplitCard):
    pile_order: ClassVar[tuple[str, ...]] = FORTS_PILE_ORDER


class Tent(_Forts):
    """+$2. You may put this on your deck."""

    upper_partners: ClassVar[tuple[str, ...]] = ()

    def __init__(self):
        super().__init__(
            name="Tent",
            cost=CardCost(coins=3),
            stats=CardStats(coins=2),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        # Always topdeck Tent so it cycles back next turn.
        if self in player.in_play:
            player.in_play.remove(self)
            player.deck.append(self)


class Garrison(_Forts):
    """+1 Action +1 Buy. Put 4 +1 Card tokens on this. At start of your
    next turn, +1 Card from each token until empty.

    Simplified: at end of cleanup it returns 4 cards next turn.
    """

    upper_partners: ClassVar[tuple[str, ...]] = ("Tent",)

    def __init__(self):
        super().__init__(
            name="Garrison",
            cost=CardCost(coins=4),
            stats=CardStats(actions=1, buys=1),
            types=[CardType.ACTION, CardType.DURATION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        # Place 4 +1 Card tokens.
        self.tokens = 4
        self.duration_persistent = True
        player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        tokens = getattr(self, "tokens", 0)
        if tokens > 0:
            game_state.draw_cards(player, tokens)
            self.tokens = 0
        self.duration_persistent = False


class HillFort(_Forts):
    """Gain a card costing up to $4. Choose: put it in your hand; or +1 Card."""

    upper_partners: ClassVar[tuple[str, ...]] = ("Tent", "Garrison")

    def __init__(self):
        super().__init__(
            name="Hill Fort",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        # Gain a card up to $4.
        candidates = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            candidate = get_card(name)
            if candidate.cost.potions > 0 or candidate.cost.coins > 4:
                continue
            if not candidate.may_be_bought(game_state):
                continue
            candidates.append(candidate)
        if not candidates:
            return
        chosen = player.ai.choose_buy(game_state, candidates + [None])
        if chosen is None:
            return
        if game_state.supply.get(chosen.name, 0) <= 0:
            return
        game_state.supply[chosen.name] -= 1
        gained = game_state.gain_card(player, chosen)
        # Choose: put in hand, or +1 Card. Prefer hand (almost always better).
        if gained in player.discard:
            player.discard.remove(gained)
            player.hand.append(gained)
        else:
            # Already routed elsewhere by reactions; fall back to +1 Card.
            game_state.draw_cards(player, 1)


class Stronghold(_Forts):
    """3 VP. Choose: +3 Cards; or +3 VP."""

    upper_partners: ClassVar[tuple[str, ...]] = ("Tent", "Garrison", "Hill Fort")

    def __init__(self):
        super().__init__(
            name="Stronghold",
            cost=CardCost(coins=6),
            stats=CardStats(vp=3),
            types=[CardType.ACTION, CardType.VICTORY],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        # +3 Cards is more useful in most positions; choose it by default.
        # If endgame is near (Provinces low), take +3 VP.
        provinces_left = game_state.supply.get("Province", 0)
        if provinces_left <= 2:
            player.vp_tokens += 3
        else:
            game_state.draw_cards(player, 3)

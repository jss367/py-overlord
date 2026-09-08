"""Odysseys split pile (Allies). Top to bottom: Old Map, Voyage,
Sunken Treasure, Distant Shore."""

from typing import ClassVar

from ..base_card import CardCost, CardStats, CardType
from ._rules import candidates, discard, gain, plus_cards, rotate
from ._split_base import AlliesSplitCard

ODYSSEYS_PILE_ORDER = ("Old Map", "Voyage", "Sunken Treasure", "Distant Shore")


class _Odysseys(AlliesSplitCard):
    pile_order: ClassVar[tuple[str, ...]] = ODYSSEYS_PILE_ORDER


class OldMap(_Odysseys):
    def __init__(self):
        super().__init__(
            name="Old Map",
            cost=CardCost(coins=3),
            stats=CardStats(cards=1, actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        p = game_state.current_player
        discard(game_state, p, 1, "old_map")
        plus_cards(game_state, p, 1)
        rotate(game_state, p, "Old Map")


class Voyage(_Odysseys):
    """+1 Action. If the previous turn wasn't yours, take an extra turn
    after this one; during that turn you can only play 3 cards from hand.
    """

    upper_partners: ClassVar[tuple[str, ...]] = ("Old Map",)

    def __init__(self):
        super().__init__(
            name="Voyage",
            cost=CardCost(coins=4),
            stats=CardStats(actions=1),
            types=[CardType.ACTION, CardType.DURATION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        if (
            not getattr(player, "outpost_pending", False)
            and not getattr(player, "outpost_taken_last_turn", False)
            and not getattr(player, "took_extra_turn_last_turn", False)
        ):
            player.voyage_extra_turn_pending = True
            game_state.extra_turn = True

        self.duration_persistent = False
        player.duration.append(self)


class SunkenTreasure(_Odysseys):
    def __init__(self):
        super().__init__(
            name="Sunken Treasure",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.TREASURE],
        )

    def play_effect(self, game_state):
        p = game_state.current_player
        names = {c.name for c in p.in_play + p.duration}
        gain(
            game_state,
            p,
            candidates(
                game_state, predicate=lambda c: c.is_action and c.name not in names
            ),
        )


class DistantShore(_Odysseys):
    def __init__(self):
        super().__init__(
            name="Distant Shore",
            cost=CardCost(coins=6),
            stats=CardStats(cards=2, actions=1, vp=2),
            types=[CardType.ACTION, CardType.VICTORY],
        )

    def play_effect(self, game_state):
        p = game_state.current_player
        gain(
            game_state,
            p,
            candidates(game_state, predicate=lambda c: c.name == "Estate"),
        )

"""Odysseys split pile (Allies). Top to bottom: Old Map, Voyage,
Sunken Treasure, Distant Shore."""

from typing import ClassVar

from ..base_card import Card, CardCost, CardStats, CardType
from ..plunder import LOOT_CARD_NAMES
from ._split_base import AlliesSplitCard

ODYSSEYS_PILE_ORDER = ("Old Map", "Voyage", "Sunken Treasure", "Distant Shore")


class _Odysseys(AlliesSplitCard):
    pile_order: ClassVar[tuple[str, ...]] = ODYSSEYS_PILE_ORDER


class OldMap(_Odysseys):
    """+1 Card +1 Action. Discard a card; +1 Card."""

    upper_partners: ClassVar[tuple[str, ...]] = ()

    def __init__(self):
        super().__init__(
            name="Old Map",
            cost=CardCost(coins=3),
            stats=CardStats(actions=1, cards=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        if not player.hand:
            return
        picks = player.ai.choose_cards_to_discard(
            game_state, player, list(player.hand), 1, reason="old_map"
        )
        if picks:
            target = picks[0]
            if target in player.hand:
                player.hand.remove(target)
                game_state.discard_card(player, target)
        game_state.draw_cards(player, 1)


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
    """Gain a non-Treasure non-supply Treasure (Loot from Plunder).
    Else gain a Gold."""

    upper_partners: ClassVar[tuple[str, ...]] = ("Old Map", "Voyage")

    def __init__(self):
        super().__init__(
            name="Sunken Treasure",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        import random as _random

        from ..registry import get_card

        player = game_state.current_player
        loot_available = [
            name for name in LOOT_CARD_NAMES
            if game_state.supply.get(name, 0) > 0
        ]
        if loot_available:
            name = _random.choice(loot_available)
            game_state.supply[name] -= 1
            game_state.gain_card(player, get_card(name))
            return
        if game_state.supply.get("Gold", 0) > 0:
            game_state.supply["Gold"] -= 1
            game_state.gain_card(player, get_card("Gold"))


class DistantShore(_Odysseys):
    """2 VP. +2 Cards +1 Action. When you gain this, gain 2 Estates."""

    upper_partners: ClassVar[tuple[str, ...]] = (
        "Old Map",
        "Voyage",
        "Sunken Treasure",
    )

    def __init__(self):
        super().__init__(
            name="Distant Shore",
            cost=CardCost(coins=6),
            stats=CardStats(actions=1, cards=2, vp=2),
            types=[CardType.ACTION, CardType.VICTORY],
        )

    def on_gain(self, game_state, player):
        from ..registry import get_card

        super().on_gain(game_state, player)
        for _ in range(2):
            if game_state.supply.get("Estate", 0) <= 0:
                break
            game_state.supply["Estate"] -= 1
            game_state.gain_card(player, get_card("Estate"))

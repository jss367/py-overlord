"""Clashes split pile (Allies expansion).

Top to bottom: Battle Plan, Archer, Warlord, Territory.
"""

from typing import ClassVar

from ..base_card import CardCost, CardStats, CardType
from ._rules import decide, plus_cards, rotate
from ._split_base import AlliesSplitCard

CLASHES_PILE_ORDER = ("Battle Plan", "Archer", "Warlord", "Territory")


class _Clashes(AlliesSplitCard):
    pile_order: ClassVar[tuple[str, ...]] = CLASHES_PILE_ORDER


class BattlePlan(_Clashes):
    def __init__(self):
        super().__init__(
            name="Battle Plan",
            cost=CardCost(coins=3),
            stats=CardStats(cards=1, actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        p = game_state.current_player
        attacks = [c for c in p.hand if c.is_attack]
        if attacks and decide(game_state, p, "battle_plan_reveal", [False, True], True):
            plus_cards(game_state, p, 1)
        rotate(game_state, p, None)


class Archer(_Clashes):
    def __init__(self):
        super().__init__(
            name="Archer",
            cost=CardCost(coins=4),
            stats=CardStats(coins=2),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        p = game_state.current_player

        def attack(target):
            if len(target.hand) < 5:
                return
            safe = decide(
                game_state,
                target,
                "archer_protect",
                list(target.hand),
                max(target.hand, key=lambda c: (c.cost.coins, c.name)),
            )
            revealed = [c for c in target.hand if c is not safe]
            chosen = decide(
                game_state,
                p,
                "archer_discard",
                revealed,
                max(revealed, key=lambda c: (c.cost.coins, c.name)),
            )
            target.hand.remove(chosen)
            game_state.discard_card(target, chosen)

        for target in game_state.opponents_in_order(p):
            game_state.attack_player(target, attack, attacker=p, attack_card=self)


class Warlord(_Clashes):
    def __init__(self):
        super().__init__(
            name="Warlord",
            cost=CardCost(coins=5),
            stats=CardStats(actions=1),
            types=[CardType.ACTION, CardType.ATTACK, CardType.DURATION],
        )
        self._warlord_targets = []

    def play_effect(self, game_state):
        p = game_state.current_player

        def attack(target):
            target.warlord_restriction_count = (
                getattr(target, "warlord_restriction_count", 0) + 1
            )
            self._warlord_targets.append(target)

        for target in game_state.opponents_in_order(p):
            game_state.attack_player(target, attack, attacker=p, attack_card=self)
        p.duration.append(self)

    def on_duration(self, game_state):
        for target in self._warlord_targets:
            target.warlord_restriction_count = max(
                0, target.warlord_restriction_count - 1
            )
        self._warlord_targets = []
        game_state.draw_cards(game_state.current_player, 2)


class Territory(_Clashes):
    """1 VP per differently-named Victory card you have.
    When you gain this, gain a Gold per empty Supply pile."""

    upper_partners: ClassVar[tuple[str, ...]] = (
        "Battle Plan",
        "Archer",
        "Warlord",
    )

    def __init__(self):
        super().__init__(
            name="Territory",
            cost=CardCost(coins=6),
            stats=CardStats(),
            types=[CardType.VICTORY],
        )

    def get_victory_points(self, player) -> int:
        names: set[str] = set()
        for card in player.all_cards():
            if card.is_victory:
                names.add(card.name)
        return len(names)

    def on_gain(self, game_state, player):
        from ..registry import get_card

        super().on_gain(game_state, player)
        empty = game_state.empty_piles
        for _ in range(empty):
            if game_state.supply.get("Gold", 0) <= 0:
                break
            game_state.supply["Gold"] -= 1
            game_state.gain_card(player, get_card("Gold"))

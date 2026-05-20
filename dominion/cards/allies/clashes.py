"""Clashes split pile (Allies expansion). All four are Liaisons.

Top to bottom: Battle Plan, Archer, Warlord, Territory.
"""

from typing import ClassVar

from ..base_card import Card, CardCost, CardStats, CardType
from ._split_base import AlliesSplitCard, grant_favor

CLASHES_PILE_ORDER = ("Battle Plan", "Archer", "Warlord", "Territory")


class _Clashes(AlliesSplitCard):
    pile_order: ClassVar[tuple[str, ...]] = CLASHES_PILE_ORDER


class BattlePlan(_Clashes):
    """+1 Card +1 Action +1 Favor. You may reveal an Attack from hand to gain another."""

    upper_partners: ClassVar[tuple[str, ...]] = ()

    def __init__(self):
        super().__init__(
            name="Battle Plan",
            cost=CardCost(coins=3),
            stats=CardStats(actions=1, cards=1),
            types=[CardType.ACTION, CardType.LIAISON],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        grant_favor(player)

        attacks = [c for c in player.hand if c.is_attack]
        if not attacks:
            return
        # Gain another copy of one of the revealed Attacks (typically the
        # most expensive Attack).
        target = max(attacks, key=lambda c: (c.cost.coins, c.name))
        if game_state.supply.get(target.name, 0) <= 0:
            return
        game_state.supply[target.name] -= 1
        game_state.gain_card(player, get_card(target.name))


class Archer(_Clashes):
    """+1 Favor +$2. Each other player with 5+ cards reveals all but one
    and discards a chosen one."""

    upper_partners: ClassVar[tuple[str, ...]] = ("Battle Plan",)

    def __init__(self):
        super().__init__(
            name="Archer",
            cost=CardCost(coins=4),
            stats=CardStats(coins=2),
            types=[CardType.ACTION, CardType.ATTACK, CardType.LIAISON],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        grant_favor(player)

        for opponent in game_state.players:
            if opponent is player:
                continue

            def attack(target):
                if len(target.hand) < 5:
                    return
                # Active player picks a card to discard from the
                # opponent's hand; default to the worst card from the
                # active player's perspective (highest cost).
                hand = list(target.hand)
                pick = max(hand, key=lambda c: (c.cost.coins, c.is_action, c.name))
                if pick in target.hand:
                    target.hand.remove(pick)
                    game_state.discard_card(target, pick)

            game_state.attack_player(opponent, attack)


class Warlord(_Clashes):
    """+1 Favor +1 Action +2 Cards. Until your next turn, no opponent
    may play any Action cards more than 2 of which are in their play area.
    """

    upper_partners: ClassVar[tuple[str, ...]] = ("Battle Plan", "Archer")

    def __init__(self):
        super().__init__(
            name="Warlord",
            cost=CardCost(coins=5),
            stats=CardStats(actions=1, cards=2),
            types=[
                CardType.ACTION,
                CardType.ATTACK,
                CardType.DURATION,
                CardType.LIAISON,
            ],
        )
        self._warlord_targets = []

    def play_effect(self, game_state):
        player = game_state.current_player
        grant_favor(player)

        def attack(target):
            target.warlord_restriction_count = (
                getattr(target, "warlord_restriction_count", 0) + 1
            )
            self._warlord_targets.append(target)

        for opponent in game_state.players:
            if opponent is player:
                continue
            game_state.attack_player(
                opponent,
                attack,
                attacker=player,
                attack_card=self,
            )

        # Stay in play through next turn (Duration). No on_duration effect.
        self.duration_persistent = False
        if self not in player.duration:
            player.duration.append(self)

    def on_duration(self, game_state):
        for target in self._warlord_targets:
            count = getattr(target, "warlord_restriction_count", 0)
            if count <= 1:
                target.warlord_restriction_count = 0
            else:
                target.warlord_restriction_count = count - 1
        self._warlord_targets = []
        # Lingering presence ends; Duration cards naturally move to
        # discard via cleanup.
        self.duration_persistent = False


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
            types=[CardType.VICTORY, CardType.LIAISON],
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

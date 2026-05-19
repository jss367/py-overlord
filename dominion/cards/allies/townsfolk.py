"""Townsfolk split pile (Allies). All four are Liaisons.

Top to bottom: Town Crier, Blacksmith, Miller, Elder.
"""

from typing import ClassVar

from ..base_card import Card, CardCost, CardStats, CardType
from ._split_base import AlliesSplitCard, grant_favor

TOWNSFOLK_PILE_ORDER = ("Town Crier", "Blacksmith", "Miller", "Elder")
_ELDER_EXTRA_CHOICE_ATTR = "_elder_extra_townsfolk_choices"


def _elder_extra_choice_count(game_state) -> int:
    return max(0, int(getattr(game_state, _ELDER_EXTRA_CHOICE_ATTR, 0) or 0))


def _append_elder_extra_modes(
    modes: list[str],
    ranked_modes: list[str],
    game_state,
) -> list[str]:
    remaining = _elder_extra_choice_count(game_state)
    for mode in ranked_modes:
        if remaining <= 0:
            break
        if mode in modes:
            continue
        modes.append(mode)
        remaining -= 1
    return modes


class _Townsfolk(AlliesSplitCard):
    pile_order: ClassVar[tuple[str, ...]] = TOWNSFOLK_PILE_ORDER


class TownCrier(_Townsfolk):
    """+1 Favor. Choose: +$2; or gain a Silver; or +1 Card +1 Action."""

    upper_partners: ClassVar[tuple[str, ...]] = ()

    def __init__(self):
        super().__init__(
            name="Town Crier",
            cost=CardCost(coins=3),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.LIAISON],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        grant_favor(player)

        modes = [self._choose_mode(game_state, player)]
        modes = _append_elder_extra_modes(
            modes,
            self._ranked_extra_modes(game_state, player),
            game_state,
        )

        for mode in modes:
            if mode == "cycle":
                if not player.ignore_action_bonuses:
                    player.actions += 1
                game_state.draw_cards(player, 1)
            elif mode == "silver":
                if game_state.supply.get("Silver", 0) > 0:
                    game_state.supply["Silver"] -= 1
                    game_state.gain_card(player, get_card("Silver"))
            elif mode == "coins":
                player.coins += 2

    @staticmethod
    def _choose_mode(game_state, player) -> str:
        # Heuristic: cycle (+1 Card +1 Action) when low actions; +$2
        # otherwise. Gain Silver only when deck is starved for treasure.
        if player.actions == 0:
            return "cycle"
        treasures_in_deck = sum(1 for c in player.all_cards() if c.is_treasure)
        if treasures_in_deck < 5 and game_state.supply.get("Silver", 0) > 0:
            return "silver"
        return "coins"

    @staticmethod
    def _ranked_extra_modes(game_state, player) -> list[str]:
        ranked: list[str] = []
        if player.actions == 0:
            ranked.append("cycle")
        treasures_in_deck = sum(1 for c in player.all_cards() if c.is_treasure)
        if treasures_in_deck < 5 and game_state.supply.get("Silver", 0) > 0:
            ranked.append("silver")
        ranked.append("coins")
        ranked.append("cycle")
        if game_state.supply.get("Silver", 0) > 0:
            ranked.append("silver")
        return ranked


class Blacksmith(_Townsfolk):
    """+1 Favor. Choose: +1 Card +1 Action; or +2 Cards; or your hand size to 6."""

    upper_partners: ClassVar[tuple[str, ...]] = ("Town Crier",)

    def __init__(self):
        super().__init__(
            name="Blacksmith",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.LIAISON],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        grant_favor(player)

        modes = [self._choose_mode(player)]
        modes = _append_elder_extra_modes(
            modes,
            self._ranked_extra_modes(player),
            game_state,
        )

        for mode in modes:
            if mode == "to_six":
                game_state.draw_cards(player, max(0, 6 - len(player.hand)))
            elif mode == "cycle":
                if not player.ignore_action_bonuses:
                    player.actions += 1
                game_state.draw_cards(player, 1)
            elif mode == "cards2":
                game_state.draw_cards(player, 2)

    @staticmethod
    def _choose_mode(player) -> str:
        # Choose by best draw value.
        hand_size = len(player.hand)
        target_six = max(0, 6 - hand_size)
        if target_six > 2:
            # Hand size to 6 wins when current hand <= 3.
            return "to_six"
        if player.actions == 0 and hand_size < 6:
            # Need an action to keep going.
            return "cycle"
        return "cards2"

    @staticmethod
    def _ranked_extra_modes(player) -> list[str]:
        hand_size = len(player.hand)
        ranked: list[str] = []
        if max(0, 6 - hand_size) > 2:
            ranked.append("to_six")
        if player.actions == 0 and hand_size < 6:
            ranked.append("cycle")
        ranked.append("cards2")
        ranked.append("cycle")
        ranked.append("to_six")
        return ranked


class Miller(_Townsfolk):
    """+1 Favor. Look at top 4 cards; put one in hand and discard rest."""

    upper_partners: ClassVar[tuple[str, ...]] = ("Town Crier", "Blacksmith")

    def __init__(self):
        super().__init__(
            name="Miller",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.LIAISON],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        grant_favor(player)

        revealed = []
        for _ in range(4):
            if not player.deck and player.discard:
                player.shuffle_discard_into_deck()
            if not player.deck:
                break
            revealed.append(player.deck.pop())
        if not revealed:
            return
        # Pick the highest-value card to keep.
        keep = max(
            revealed,
            key=lambda c: (
                c.is_action,
                c.is_treasure,
                c.cost.coins,
                c.stats.cards * 2 + c.stats.actions + c.stats.coins,
                c.name,
            ),
        )
        revealed.remove(keep)
        player.hand.append(keep)
        for card in revealed:
            game_state.discard_card(player, card)


class Elder(_Townsfolk):
    """+1 Favor +1 Action. You may play an Action card from your hand;
    when it gives a choice of abilities, choose one extra.

    The engine has no shared metadata for arbitrary card choices, so this
    module implements the extra-choice context for the Townsfolk choice
    cards that can observe it. Other cards still resolve through their own
    normal play APIs.
    """

    upper_partners: ClassVar[tuple[str, ...]] = (
        "Town Crier",
        "Blacksmith",
        "Miller",
    )

    def __init__(self):
        super().__init__(
            name="Elder",
            cost=CardCost(coins=6),
            stats=CardStats(actions=1),
            types=[CardType.ACTION, CardType.LIAISON],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        grant_favor(player)

        actions_in_hand = [c for c in player.hand if c.is_action]
        if not actions_in_hand:
            return
        choice = player.ai.choose_action(game_state, actions_in_hand + [None])
        if choice is None or choice not in player.hand:
            return
        if not game_state.move_card_from_hand_to_play(player, choice):
            return
        previous = getattr(game_state, _ELDER_EXTRA_CHOICE_ATTR, 0)
        setattr(game_state, _ELDER_EXTRA_CHOICE_ATTR, previous + 1)
        try:
            game_state.play_action_indirectly(player, choice)
        finally:
            if previous:
                setattr(game_state, _ELDER_EXTRA_CHOICE_ATTR, previous)
            else:
                try:
                    delattr(game_state, _ELDER_EXTRA_CHOICE_ATTR)
                except AttributeError:
                    pass

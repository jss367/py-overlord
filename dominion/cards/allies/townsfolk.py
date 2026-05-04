"""Townsfolk split pile (Allies). All four are Liaisons.

Top to bottom: Town Crier, Blacksmith, Miller, Elder.
"""

from typing import ClassVar

from ..base_card import Card, CardCost, CardStats, CardType
from ._split_base import AlliesSplitCard, grant_favor

TOWNSFOLK_PILE_ORDER = ("Town Crier", "Blacksmith", "Miller", "Elder")


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

        # Heuristic: cycle (+1 Card +1 Action) when low actions; +$2
        # otherwise. Gain Silver only when deck is starved for treasure.
        if player.actions == 0:
            if not player.ignore_action_bonuses:
                player.actions += 1
            game_state.draw_cards(player, 1)
            return
        treasures_in_deck = sum(1 for c in player.all_cards() if c.is_treasure)
        if treasures_in_deck < 5 and game_state.supply.get("Silver", 0) > 0:
            game_state.supply["Silver"] -= 1
            game_state.gain_card(player, get_card("Silver"))
            return
        player.coins += 2


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

        # Choose by best draw value.
        hand_size = len(player.hand)
        target_six = max(0, 6 - hand_size)
        if target_six > 2:
            # Hand size to 6 wins when current hand <= 3.
            game_state.draw_cards(player, target_six)
        elif player.actions == 0 and hand_size < 6:
            # Need an action to keep going.
            if not player.ignore_action_bonuses:
                player.actions += 1
            game_state.draw_cards(player, 1)
        else:
            game_state.draw_cards(player, 2)


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
    when its choices include 'choose one or more', choose one extra.

    Simplified: play an Action from hand (the "choose one extra" clause
    is hard to implement without per-card choice metadata; the +Action
    +Favor still trigger).
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
        player.hand.remove(choice)
        player.in_play.append(choice)
        choice.on_play(game_state)
        game_state.fire_ally_play_hooks(player, choice)

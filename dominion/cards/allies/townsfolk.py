"""Townsfolk split pile (Allies).

Top to bottom: Town Crier, Blacksmith, Miller, Elder.
"""

from typing import ClassVar

from ..base_card import CardCost, CardStats, CardType
from ._rules import candidates, gain, plus_cards, plus_coins, rotate, select_modes
from ._split_base import AlliesSplitCard

TOWNSFOLK_PILE_ORDER = ("Town Crier", "Blacksmith", "Miller", "Elder")


class _Townsfolk(AlliesSplitCard):
    pile_order: ClassVar[tuple[str, ...]] = TOWNSFOLK_PILE_ORDER


class TownCrier(_Townsfolk):
    def __init__(self):
        super().__init__(
            name="Town Crier",
            cost=CardCost(coins=2),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        p = game_state.current_player
        default = "cycle" if p.actions == 0 else "coins"
        for mode in select_modes(
            game_state, p, self, ["coins", "silver", "cycle"], [default]
        ):
            if mode == "coins":
                plus_coins(p, 2)
            elif mode == "silver":
                gain(
                    game_state,
                    p,
                    candidates(game_state, predicate=lambda c: c.name == "Silver"),
                )
            else:
                plus_cards(game_state, p, 1)
                if not p.ignore_action_bonuses:
                    p.actions += 1
        rotate(game_state, p, "Town Crier")


class Blacksmith(_Townsfolk):
    def __init__(self):
        super().__init__(
            name="Blacksmith",
            cost=CardCost(coins=3),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        p = game_state.current_player
        default = (
            "to_six" if len(p.hand) < 4 else "cycle" if p.actions == 0 else "cards2"
        )
        for mode in select_modes(
            game_state, p, self, ["to_six", "cards2", "cycle"], [default]
        ):
            if mode == "to_six":
                game_state.draw_cards(p, max(0, 6 - len(p.hand)))
            elif mode == "cards2":
                plus_cards(game_state, p, 2)
            else:
                plus_cards(game_state, p, 1)
                if not p.ignore_action_bonuses:
                    p.actions += 1


class Miller(_Townsfolk):
    """+1 Action. Look at top 4 cards; put one in hand and discard rest."""

    upper_partners: ClassVar[tuple[str, ...]] = ("Town Crier", "Blacksmith")

    def __init__(self):
        super().__init__(
            name="Miller",
            cost=CardCost(coins=4),
            stats=CardStats(actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

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
    def __init__(self):
        super().__init__(
            name="Elder",
            cost=CardCost(coins=5),
            stats=CardStats(coins=2),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        p = game_state.current_player
        actions = [c for c in p.hand if c.is_action]
        choice = p.ai.choose_action(game_state, actions + [None])
        if choice not in actions or not game_state.move_card_from_hand_to_play(
            p, choice
        ):
            return
        if not hasattr(p, "elder_choices"):
            p.elder_choices = {}
        p.elder_choices[choice] = p.elder_choices.get(choice, 0) + 1
        game_state.play_action_indirectly(p, choice, blocked_return_zone=p.hand)

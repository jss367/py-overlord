"""Augurs split pile (Allies expansion).

Top to bottom: Herb Gatherer, Acolyte, Sorceress, Sibyl. Only the top
card with copies remaining may be bought.
"""

from typing import ClassVar

from ..base_card import CardCost, CardStats, CardType
from ._rules import candidates, decide, effective_cost, gain, rotate
from ._split_base import AlliesSplitCard

AUGURS_PILE_ORDER = ("Herb Gatherer", "Acolyte", "Sorceress", "Sibyl")


class _Augurs(AlliesSplitCard):
    pile_order: ClassVar[tuple[str, ...]] = AUGURS_PILE_ORDER


class HerbGatherer(_Augurs):
    def __init__(self):
        super().__init__(
            name="Herb Gatherer",
            cost=CardCost(coins=3),
            stats=CardStats(buys=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        p = game_state.current_player
        p.discard.extend(p.deck)
        p.deck = []
        choices = [c for c in p.discard if game_state.is_treasure(c)]
        default = p.ai.choose_treasure(game_state, choices + [None])
        choice = decide(
            game_state, p, "herb_gatherer_treasure", [None] + choices, default
        )
        if choice in choices:
            p.discard.remove(choice)
            p.in_play.append(choice)
            game_state.play_treasure_indirectly(p, choice)
        rotate(game_state, p, "Herb Gatherer")


class Acolyte(_Augurs):
    def __init__(self):
        super().__init__(
            name="Acolyte",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        p = game_state.current_player
        eligible = [c for c in p.hand if c.is_action or c.is_victory]
        default = (
            min(eligible, key=lambda c: effective_cost(game_state, c).coins)
            if eligible
            else None
        )
        target = decide(game_state, p, "acolyte_trash", [None] + eligible, default)
        if target is not None:
            p.hand.remove(target)
            game_state.trash_card(p, target)
            gain(
                game_state,
                p,
                candidates(game_state, predicate=lambda c: c.name == "Gold"),
            )
        if self in p.in_play and decide(
            game_state, p, "acolyte_trash_self", [False, True], False
        ):
            p.in_play.remove(self)
            game_state.trash_card(p, self)
            gain(
                game_state,
                p,
                candidates(game_state, predicate=lambda c: c.name in AUGURS_PILE_ORDER),
            )


class Sorceress(_Augurs):
    """+1 Action. Name a card. Reveal top of deck.
    Put it into your hand; if it matches, each other player gains a Curse.
    """

    upper_partners: ClassVar[tuple[str, ...]] = ("Herb Gatherer", "Acolyte")

    def __init__(self):
        super().__init__(
            name="Sorceress",
            cost=CardCost(coins=5),
            stats=CardStats(actions=1),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        named = player.ai.name_card_for_wishing_well(game_state, player)

        if not player.deck and player.discard:
            player.shuffle_discard_into_deck()
        if not player.deck:
            return

        revealed = player.deck.pop()
        player.hand.append(revealed)
        if not named or revealed.name != named:
            return

        def curse_target(target):
            game_state.give_curse_to_player(target)

        for opponent in game_state.players:
            if opponent is player:
                continue
            game_state.attack_player(
                opponent,
                curse_target,
                attacker=player,
                attack_card=self,
            )


class Sibyl(_Augurs):
    """+4 Cards, +1 Action. Topdeck a card from hand, then bottomdeck one."""

    upper_partners: ClassVar[tuple[str, ...]] = (
        "Herb Gatherer",
        "Acolyte",
        "Sorceress",
    )

    def __init__(self):
        super().__init__(
            name="Sibyl",
            cost=CardCost(coins=6),
            stats=CardStats(cards=4, actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        if not player.hand:
            return

        # Topdeck the best card from hand for next turn.
        topdeck = player.ai.choose_card_to_topdeck_from_hand(
            game_state, player, list(player.hand), reason="sibyl"
        )
        if topdeck not in player.hand:
            topdeck = player.hand[0]
        if topdeck in player.hand:
            player.hand.remove(topdeck)
            player.deck.append(topdeck)

        # Bottom-deck the worst card from hand.
        if not player.hand:
            return
        picks = player.ai.choose_cards_to_discard(
            game_state, player, list(player.hand), 1, reason="sibyl_bottom"
        )
        if not picks or picks[0] not in player.hand:
            picks = [player.hand[0]]
        if picks:
            bottom = picks[0]
            if bottom in player.hand:
                player.hand.remove(bottom)
                player.deck.insert(0, bottom)

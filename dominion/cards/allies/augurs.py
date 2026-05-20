"""Augurs split pile (Allies expansion).

Top to bottom: Herb Gatherer, Acolyte, Sorceress, Sibyl. Only the top
card with copies remaining may be bought.
"""

from typing import ClassVar

from ..base_card import Card, CardCost, CardStats, CardType
from ._split_base import AlliesSplitCard

AUGURS_PILE_ORDER = ("Herb Gatherer", "Acolyte", "Sorceress", "Sibyl")


class _Augurs(AlliesSplitCard):
    pile_order: ClassVar[tuple[str, ...]] = AUGURS_PILE_ORDER


class HerbGatherer(_Augurs):
    """+1 Buy. You may put your discard into your deck."""

    upper_partners: ClassVar[tuple[str, ...]] = ()

    def __init__(self):
        super().__init__(
            name="Herb Gatherer",
            cost=CardCost(coins=3),
            stats=CardStats(buys=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        if not player.discard:
            return
        # Always opt in: putting the discard onto the deck is a soft draw
        # boost; the AI then plays through it next.
        player.deck.extend(player.discard)
        player.discard = []


class Acolyte(_Augurs):
    """You may trash a Victory card from hand for a Gold.
    Once per turn, when you trash an Acolyte, gain an Augurs card.
    """

    upper_partners: ClassVar[tuple[str, ...]] = ("Herb Gatherer",)

    def __init__(self):
        super().__init__(
            name="Acolyte",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        victories = [c for c in player.hand if c.is_victory]
        if not victories:
            return
        target = min(victories, key=lambda c: (c.cost.coins, c.name))
        player.hand.remove(target)
        game_state.trash_card(player, target)
        if game_state.supply.get("Gold", 0) > 0:
            game_state.supply["Gold"] -= 1
            game_state.gain_card(player, get_card("Gold"))

    def on_trash(self, game_state, player) -> None:
        from ..registry import get_card

        # Once per turn: gain an Augurs card.
        if getattr(player, "acolyte_trashed_this_turn", False):
            return
        player.acolyte_trashed_this_turn = True
        candidates = [
            name for name in AUGURS_PILE_ORDER
            if game_state.supply.get(name, 0) > 0
        ]
        if not candidates:
            return
        # Pick the most expensive Augurs card available.
        best = max(candidates, key=lambda n: AUGURS_PILE_ORDER.index(n))
        try:
            card = get_card(best)
        except ValueError:
            return
        if not card.may_be_bought(game_state):
            # Drain order means only the topmost is buyable; pick the
            # earliest one available instead.
            for name in AUGURS_PILE_ORDER:
                if game_state.supply.get(name, 0) > 0:
                    candidate = get_card(name)
                    if candidate.may_be_bought(game_state):
                        card = candidate
                        break
            else:
                return
        if game_state.supply.get(card.name, 0) <= 0:
            return
        game_state.supply[card.name] -= 1
        game_state.gain_card(player, card)


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
    """+4 Cards. Put a card from your hand on top of deck, and one on bottom."""

    upper_partners: ClassVar[tuple[str, ...]] = (
        "Herb Gatherer",
        "Acolyte",
        "Sorceress",
    )

    def __init__(self):
        super().__init__(
            name="Sibyl",
            cost=CardCost(coins=6),
            stats=CardStats(cards=4),
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
        if topdeck is not None and topdeck in player.hand:
            player.hand.remove(topdeck)
            player.deck.append(topdeck)

        # Bottom-deck the worst card from hand.
        if not player.hand:
            return
        picks = player.ai.choose_cards_to_discard(
            game_state, player, list(player.hand), 1, reason="sibyl_bottom"
        )
        if picks:
            bottom = picks[0]
            if bottom in player.hand:
                player.hand.remove(bottom)
                player.deck.insert(0, bottom)

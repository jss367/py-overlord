"""Wizards split pile: Student / Conjurer / Sorcerer / Lich.

Only Student is a Liaison. Rotation changes which card is available.
"""

from collections import Counter
from typing import Optional

from ..base_card import Card, CardCost, CardStats, CardType
from ._rules import candidates, cheaper, effective_cost, gain, rotate, trash_from_hand

# Order from top of pile to bottom.
WIZARDS_PILE_ORDER = ("Student", "Conjurer", "Sorcerer", "Lich")


from ._split_base import AlliesSplitCard


class WizardsSplitCard(AlliesSplitCard):
    pile_order = WIZARDS_PILE_ORDER


class Student(WizardsSplitCard):
    def __init__(self):
        super().__init__(
            name="Student",
            cost=CardCost(coins=3),
            stats=CardStats(actions=1),
            types=[CardType.ACTION, CardType.LIAISON],
        )

    def play_effect(self, game_state):
        p = game_state.current_player
        rotate(game_state, p, "Student")
        target = trash_from_hand(game_state, p)
        if target is not None and game_state.is_treasure(target):
            p.favors += 1
            if self in p.in_play:
                p.in_play.remove(self)
                p.deck.append(self)


class Conjurer(WizardsSplitCard):
    def __init__(self):
        super().__init__(
            name="Conjurer",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.DURATION],
        )

    def play_effect(self, game_state):
        p = game_state.current_player
        gain(game_state, p, candidates(game_state, CardCost(coins=4)))
        p.duration.append(self)

    def on_duration(self, game_state):
        p = game_state.current_player
        if self in p.in_play:
            p.in_play.remove(self)
            p.hand.append(self)


class Sorcerer(WizardsSplitCard):
    """+1 Card, +1 Action. Each other player names and reveals a card.

    Each other player names a card, reveals the top card of their deck, and
    gains a Curse if the revealed card is not the named card.
    """

    upper_partners = ("Student", "Conjurer")

    def __init__(self):
        super().__init__(
            name="Sorcerer",
            cost=CardCost(coins=5),
            stats=CardStats(actions=1, cards=1),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player

        for opponent in game_state.players:
            if opponent is player:
                continue

            def attack(target):
                named = self._name_card(game_state, target)
                revealed = self._peek_top_after_shuffle(target)
                if revealed is None or revealed.name == named:
                    return
                if game_state.supply.get("Curse", 0) <= 0:
                    return
                game_state.supply["Curse"] -= 1
                curse = get_card("Curse")
                game_state.gain_card(target, curse)

            game_state.attack_player(opponent, attack)

    @staticmethod
    def _peek_top_after_shuffle(player) -> Optional[Card]:
        if not player.deck and player.discard:
            player.shuffle_discard_into_deck()
        if not player.deck:
            return None
        return player.deck[-1]

    @staticmethod
    def _name_card(game_state, player) -> Optional[str]:
        # Sorcerer's choice has the same strategic shape as Wishing Well:
        # name a card before revealing the top of your own deck. Prefer that
        # hook when available, while allowing dedicated AIs to specialize.
        for hook_name in (
            "name_card_for_sorcerer",
            "name_card_for_wishing_well",
            "name_card_for_mystic",
        ):
            hook = getattr(player.ai, hook_name, None)
            if hook is not None:
                return hook(game_state, player)

        counts = Counter(card.name for card in player.deck)
        if not counts and player.discard:
            counts = Counter(card.name for card in player.discard)
        if not counts:
            return None
        return max(counts.items(), key=lambda kv: (kv[1], kv[0]))[0]


class Lich(WizardsSplitCard):
    def __init__(self):
        super().__init__(
            name="Lich",
            cost=CardCost(coins=6),
            stats=CardStats(cards=6, actions=2),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        p = game_state.current_player
        p.turns_to_skip = getattr(p, "turns_to_skip", 0) + 1

    def on_trash(self, game_state, player):
        from ._rules import choose_gain

        if self in game_state.trash:
            game_state.trash.remove(self)
            game_state.discard_card(player, self)
        choices = [
            c
            for c in game_state.trash
            if cheaper(effective_cost(game_state, c), effective_cost(game_state, self))
        ]
        choice = choose_gain(game_state, player, choices)
        if choice is not None:
            game_state.trash.remove(choice)
            game_state.gain_card(player, choice, from_supply=False)

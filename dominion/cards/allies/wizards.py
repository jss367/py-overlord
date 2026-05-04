"""Wizards split pile: Student / Conjurer / Sorcerer / Lich.

All four are Liaisons (grant +1 Favor when played). The pile drains in order
Student → Conjurer → Sorcerer → Lich; only the topmost still-stocked card is
buyable.
"""

from typing import Optional

from ..base_card import Card, CardCost, CardStats, CardType


# Order from top of pile to bottom.
WIZARDS_PILE_ORDER = ("Student", "Conjurer", "Sorcerer", "Lich")


class WizardsSplitCard(Card):
    """Common base for the Wizards split pile."""

    upper_partners: tuple[str, ...] = ()

    def starting_supply(self, game_state) -> int:
        return 4 if len(game_state.players) <= 2 else 5

    def may_be_bought(self, game_state) -> bool:
        for partner in self.upper_partners:
            if game_state.supply.get(partner, 0) > 0:
                return False
        return super().may_be_bought(game_state)

    # Note: the partner Wizards aren't added via ``get_additional_piles``
    # because that method has no access to ``game_state`` and so can't size
    # the piles by player count. Instead, ``GameState.setup_supply`` detects
    # ``WizardsSplitCard`` and calls ``starting_supply`` on each partner —
    # the same shape as the existing ``SplitPileMixin`` handling. Keep this
    # default empty so the supply path stays consistent.


def _grant_favor(player) -> None:
    player.favors += 1


class Student(WizardsSplitCard):
    """+1 Action; trash a card from your hand. If a Treasure, +1 Favor."""

    upper_partners = ()

    def __init__(self):
        super().__init__(
            name="Student",
            cost=CardCost(coins=3),
            stats=CardStats(actions=1),
            types=[CardType.ACTION, CardType.LIAISON],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        _grant_favor(player)  # Liaison

        if not player.hand:
            return

        chosen = player.ai.choose_card_to_trash(game_state, player.hand)
        if chosen is None:
            return
        if chosen not in player.hand:
            return

        player.hand.remove(chosen)
        game_state.trash_card(player, chosen)

        if chosen.is_treasure:
            _grant_favor(player)
            # Student's official text: "If it's a Treasure, put this onto
            # your deck." Move Student out of in_play so cleanup doesn't
            # also discard it.
            if self in player.in_play:
                player.in_play.remove(self)
                player.deck.append(self)


class Conjurer(WizardsSplitCard):
    """+1 Card, +1 Action. Gain a card costing up to $4. (Liaison)"""

    upper_partners = ("Student",)

    def __init__(self):
        super().__init__(
            name="Conjurer",
            cost=CardCost(coins=4),
            stats=CardStats(actions=1, cards=1),
            types=[CardType.ACTION, CardType.LIAISON],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        _grant_favor(player)

        # Gain a card costing up to $4 (Conjurer-style gainer).
        candidates: list[Card] = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            card = get_card(name)
            if card.cost.potions > 0:
                continue
            if card.cost.coins > 4:
                continue
            if not card.may_be_bought(game_state):
                continue
            candidates.append(card)

        if not candidates:
            return

        chosen = player.ai.choose_buy(game_state, candidates + [None])
        if chosen is None:
            return
        if game_state.supply.get(chosen.name, 0) <= 0:
            return

        game_state.supply[chosen.name] -= 1
        game_state.gain_card(player, chosen)


class Sorcerer(WizardsSplitCard):
    """+1 Card, +1 Action. Each other player gains a Curse on top of deck.

    (Simplified: skip the "name a card / reveal top of deck" subgame and treat
    this as a guaranteed top-decked Curser. In practice the named card almost
    never matches the top of an unknown deck.)
    """

    upper_partners = ("Student", "Conjurer")

    def __init__(self):
        super().__init__(
            name="Sorcerer",
            cost=CardCost(coins=5),
            stats=CardStats(actions=1, cards=1),
            types=[CardType.ACTION, CardType.ATTACK, CardType.LIAISON],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        _grant_favor(player)

        for opponent in game_state.players:
            if opponent is player:
                continue

            def attack(target):
                if game_state.supply.get("Curse", 0) <= 0:
                    return
                game_state.supply["Curse"] -= 1
                curse = get_card("Curse")
                game_state.gain_card(target, curse, to_deck=True)

            game_state.attack_player(opponent, attack)


class Lich(WizardsSplitCard):
    """+6 Cards, +2 Actions, discard 2 cards. Gain a cheaper Action from trash.

    On trash: gain a non-Lich Action from supply costing up to $5.
    """

    upper_partners = ("Student", "Conjurer", "Sorcerer")

    def __init__(self):
        super().__init__(
            name="Lich",
            cost=CardCost(coins=6),
            stats=CardStats(actions=2, cards=6),
            types=[CardType.ACTION, CardType.LIAISON],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        _grant_favor(player)

        # Discard 2 cards (worst).
        if player.hand:
            picks = player.ai.choose_cards_to_discard(
                game_state, player, list(player.hand), 2, reason="lich"
            )
            for card in picks:
                if card in player.hand:
                    player.hand.remove(card)
                    game_state.discard_card(player, card)

        # Gain a cheaper Action from the trash.
        max_cost = self.cost.coins - 1
        candidates = [
            c
            for c in game_state.trash
            if c.is_action and c.cost.coins <= max_cost and c.cost.potions == 0
        ]
        if not candidates:
            return

        chosen: Optional[Card] = player.ai.choose_card_to_gain_from_trash(
            game_state, player, candidates, max_cost
        )
        if chosen is None or chosen not in game_state.trash:
            return
        game_state.trash.remove(chosen)
        # Route through gain_card so the gain participates in shared
        # bookkeeping (cards_gained_this_turn, actions_gained_this_turn,
        # Cauldron's third-Action-gain trigger, project on_gain hooks,
        # Watchtower / Royal Seal / Insignia reactions, …). Pass
        # from_supply=False since the card came from trash — without that,
        # Trader's reaction would inflate the original card's supply pile.
        game_state.gain_card(player, chosen, from_supply=False)

    def on_trash(self, game_state, player) -> None:
        from ..registry import get_card

        # Gain a non-Lich Action card costing up to $5 from supply.
        candidates: list[Card] = []
        for name, count in game_state.supply.items():
            if count <= 0 or name == "Lich":
                continue
            try:
                card = get_card(name)
            except ValueError:
                continue
            if not card.is_action:
                continue
            if card.cost.coins > 5 or card.cost.potions > 0:
                continue
            if not card.may_be_bought(game_state):
                continue
            candidates.append(card)

        if not candidates:
            return

        chosen = player.ai.choose_buy(game_state, candidates + [None])
        if chosen is None:
            return
        if game_state.supply.get(chosen.name, 0) <= 0:
            return

        game_state.supply[chosen.name] -= 1
        game_state.gain_card(player, chosen)

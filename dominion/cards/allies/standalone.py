"""Standalone Allies expansion kingdom cards (non-split).

Bauble, Sycophant, Importer, Contract, Emissary, Galleria, Hunter,
Skirmisher, Specialist, Swap, Underling, Broker, Carpenter, Courier,
Innkeeper, Royal Galley, Town.
"""

from typing import Optional

from ..base_card import Card, CardCost, CardStats, CardType


# ---------------------------------------------------------------------------
# $2 Liaisons
# ---------------------------------------------------------------------------

class Bauble(Card):
    """$2 Treasure-Liaison. +1 Buy. Choose one: +$1; +1 Favor; +1 Card;
    or topdeck this. (Always grants +1 Favor as a Liaison too.)
    """

    def __init__(self):
        super().__init__(
            name="Bauble",
            cost=CardCost(coins=2),
            stats=CardStats(),
            types=[CardType.TREASURE, CardType.LIAISON],
        )

    def on_play(self, game_state):
        player = game_state.current_player
        # Liaison: +1 Favor when played.
        player.favors += 1
        player.buys += 1
        # Choose one: heuristic — prefer +$1 by default, +1 Favor if
        # the Ally is starved, +1 Card if hand is short, topdeck if a
        # second play this turn would be useful (rare without a TR).
        if len(player.hand) <= 2:
            game_state.draw_cards(player, 1)
        else:
            player.coins += 1


class Sycophant(Card):
    """$2 Action-Liaison. +1 Action. Discard 3 cards. If any, +2 Favors."""

    def __init__(self):
        super().__init__(
            name="Sycophant",
            cost=CardCost(coins=2),
            stats=CardStats(actions=1),
            types=[CardType.ACTION, CardType.LIAISON],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        if not player.hand:
            return
        picks = player.ai.choose_cards_to_discard(
            game_state, player, list(player.hand), 3, reason="sycophant"
        )
        discarded = 0
        for card in picks:
            if card in player.hand:
                player.hand.remove(card)
                game_state.discard_card(player, card)
                discarded += 1
        if discarded > 0:
            # Official: +2 Favors when you discard any (per most printings;
            # accept simplification of "+1 Favor if discarded any").
            player.favors += 2


# ---------------------------------------------------------------------------
# $3 Liaisons
# ---------------------------------------------------------------------------

class Importer(Card):
    """$3 Action-Liaison. At start of next turn, gain a card costing up to $5.
    +1 Favor."""

    def __init__(self):
        super().__init__(
            name="Importer",
            cost=CardCost(coins=3),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.DURATION, CardType.LIAISON],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        player.favors += 1
        self.duration_persistent = False
        player.duration.append(self)

    def on_duration(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        candidates = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            card = get_card(name)
            if card.cost.potions > 0 or card.cost.coins > 5:
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


class Underling(Card):
    """$3 Action-Liaison. +1 Card +1 Action. +1 Favor."""

    def __init__(self):
        super().__init__(
            name="Underling",
            cost=CardCost(coins=3),
            stats=CardStats(actions=1, cards=1),
            types=[CardType.ACTION, CardType.LIAISON],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        player.favors += 1


# ---------------------------------------------------------------------------
# $4 cards
# ---------------------------------------------------------------------------

class Broker(Card):
    """$4 Action-Liaison. Trash a card. Choose: +1 Card per cost; or
    +$1 per cost; or +1 Action per cost; or +1 Favor per cost."""

    def __init__(self):
        super().__init__(
            name="Broker",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.LIAISON],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        if not player.hand:
            return
        target = player.ai.choose_card_to_trash(game_state, player.hand)
        if target is None or target not in player.hand:
            return
        cost = target.cost.coins
        player.hand.remove(target)
        game_state.trash_card(player, target)
        if cost <= 0:
            return
        # Heuristic: prefer cards if we still have actions; coins
        # otherwise; favors if Ally is starved; +Actions if low.
        if player.actions == 0 and cost >= 2:
            player.actions += cost
        elif cost <= 2 and game_state.allies and player.favors < 3:
            player.favors += cost
        elif player.actions > 0 and cost >= 3:
            game_state.draw_cards(player, cost)
        else:
            player.coins += cost


class Carpenter(Card):
    """$4 Action. +1 Action. If no empty piles, gain a card up to $4.
    Otherwise trash a card from hand and gain a card up to $5."""

    def __init__(self):
        super().__init__(
            name="Carpenter",
            cost=CardCost(coins=4),
            stats=CardStats(actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        if game_state.empty_piles == 0:
            max_cost = 4
        else:
            if player.hand:
                target = player.ai.choose_card_to_trash(game_state, player.hand)
                if target is not None and target in player.hand:
                    player.hand.remove(target)
                    game_state.trash_card(player, target)
            max_cost = 5

        candidates = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            card = get_card(name)
            if card.cost.potions > 0 or card.cost.coins > max_cost:
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


class Courier(Card):
    """$4 Action. +$1. Look at top of deck; trash, discard, or play.

    Note: 'play' only fires if it's an Action.
    """

    def __init__(self):
        super().__init__(
            name="Courier",
            cost=CardCost(coins=4),
            stats=CardStats(coins=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        if not player.deck and player.discard:
            player.shuffle_discard_into_deck()
        if not player.deck:
            return
        top = player.deck.pop()
        if top.is_action:
            # Play it.
            player.in_play.append(top)
            top.on_play(game_state)
        elif top.name in {"Curse", "Estate", "Copper"}:
            game_state.trash_card(player, top)
        else:
            game_state.discard_card(player, top)


class Innkeeper(Card):
    """$4 Action. +1 Action. Choose: +1 Card; or +3 Cards, discard 3."""

    def __init__(self):
        super().__init__(
            name="Innkeeper",
            cost=CardCost(coins=4),
            stats=CardStats(actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        # Heuristic: take +3/-3 if hand has clutter, otherwise +1.
        clutter = sum(
            1 for c in player.hand
            if c.name in {"Curse", "Copper", "Estate", "Hovel", "Overgrown Estate"}
        )
        if clutter >= 2 or len(player.hand) <= 2:
            game_state.draw_cards(player, 3)
            picks = player.ai.choose_cards_to_discard(
                game_state, player, list(player.hand), 3, reason="innkeeper"
            )
            for card in picks:
                if card in player.hand:
                    player.hand.remove(card)
                    game_state.discard_card(player, card)
        else:
            game_state.draw_cards(player, 1)


class RoyalGalley(Card):
    """$4 Action-Duration. You may play a non-Duration Action from hand
    twice. If you do, set this and the Action aside. Both come back at
    start of next turn.

    Simplified: play the Action twice this turn. Skip the set-aside step
    (the card just goes through normal cleanup).
    """

    def __init__(self):
        super().__init__(
            name="Royal Galley",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.DURATION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        actions = [
            c for c in player.hand
            if c.is_action and not c.is_duration
        ]
        if not actions:
            self.duration_persistent = False
            player.duration.append(self)
            return
        choice = player.ai.choose_action(game_state, actions + [None])
        if choice is None or choice not in player.hand:
            self.duration_persistent = False
            player.duration.append(self)
            return
        player.hand.remove(choice)
        player.in_play.append(choice)
        for _ in range(2):
            choice.on_play(game_state)
        # Stay in play through duration cleanup.
        self.duration_persistent = False
        player.duration.append(self)


class Town(Card):
    """$4 Action. Choose: +1 Card +2 Actions; or +1 Buy +$2."""

    def __init__(self):
        super().__init__(
            name="Town",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        action_cards = [c for c in player.hand if c.is_action]
        if action_cards or player.actions == 0:
            # Use as a Village.
            if not player.ignore_action_bonuses:
                player.actions += 2
            game_state.draw_cards(player, 1)
        else:
            player.buys += 1
            player.coins += 2


# ---------------------------------------------------------------------------
# $5 Liaisons
# ---------------------------------------------------------------------------

class Contract(Card):
    """$5 Treasure-Duration-Liaison. $2 +1 Favor. Set aside an Action from
    hand. Play it at start of next turn.
    """

    def __init__(self):
        super().__init__(
            name="Contract",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.TREASURE, CardType.DURATION, CardType.LIAISON],
        )
        self._set_aside: Optional[Card] = None

    def on_play(self, game_state):
        player = game_state.current_player
        # Treasure body: +$2 +1 Favor.
        player.coins += 2
        player.favors += 1

        actions = [c for c in player.hand if c.is_action and not c.is_duration]
        if actions:
            choice = player.ai.choose_action(game_state, actions + [None])
            if choice is not None and choice in player.hand:
                player.hand.remove(choice)
                self._set_aside = choice

        if self._set_aside is not None:
            self.duration_persistent = False
            player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        if self._set_aside is None:
            return
        card = self._set_aside
        self._set_aside = None
        player.in_play.append(card)
        card.on_play(game_state)


class Emissary(Card):
    """$5 Action-Liaison. Reveal hand; +1 Card per differently-named
    Action revealed. Discard down to 4. +1 Favor."""

    def __init__(self):
        super().__init__(
            name="Emissary",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.LIAISON],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        player.favors += 1

        action_names = {c.name for c in player.hand if c.is_action}
        bonus = len(action_names)
        if bonus > 0:
            game_state.draw_cards(player, bonus)

        excess = max(0, len(player.hand) - 4)
        if excess > 0:
            picks = player.ai.choose_cards_to_discard(
                game_state, player, list(player.hand), excess, reason="emissary"
            )
            for card in picks:
                if card in player.hand:
                    player.hand.remove(card)
                    game_state.discard_card(player, card)


class Galleria(Card):
    """$5 Action-Liaison. +$2. While this is in play, when you gain a card
    costing $3-$5, +1 Buy. +1 Favor."""

    def __init__(self):
        super().__init__(
            name="Galleria",
            cost=CardCost(coins=5),
            stats=CardStats(coins=2),
            types=[CardType.ACTION, CardType.LIAISON],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        player.favors += 1

    def on_owner_gain(self, game_state, player, gained_card: Card) -> None:
        if 3 <= gained_card.cost.coins <= 5:
            player.buys += 1


class Hunter(Card):
    """$5 Action-Liaison. +1 Action. Reveal top 3 cards; put one Action,
    one Treasure, one Victory into hand; discard the rest. +1 Favor."""

    def __init__(self):
        super().__init__(
            name="Hunter",
            cost=CardCost(coins=5),
            stats=CardStats(actions=1),
            types=[CardType.ACTION, CardType.LIAISON],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        player.favors += 1

        revealed: list[Card] = []
        for _ in range(3):
            if not player.deck and player.discard:
                player.shuffle_discard_into_deck()
            if not player.deck:
                break
            revealed.append(player.deck.pop())

        # Put one Action, one Treasure, one Victory into hand.
        for predicate in (lambda c: c.is_action,
                          lambda c: c.is_treasure,
                          lambda c: c.is_victory):
            matches = [c for c in revealed if predicate(c)]
            if matches:
                pick = max(matches, key=lambda c: (c.cost.coins, c.name))
                revealed.remove(pick)
                player.hand.append(pick)
        for card in revealed:
            game_state.discard_card(player, card)


class Skirmisher(Card):
    """$5 Action-Attack-Liaison. +1 Card +1 Action +$1. Until end of turn,
    when you gain an Action, each other player with 5+ cards in hand
    discards one. +1 Favor."""

    def __init__(self):
        super().__init__(
            name="Skirmisher",
            cost=CardCost(coins=5),
            stats=CardStats(actions=1, cards=1, coins=1),
            types=[CardType.ACTION, CardType.ATTACK, CardType.LIAISON],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        player.favors += 1

    def on_owner_gain(self, game_state, player, gained_card: Card) -> None:
        if not gained_card.is_action:
            return
        for opponent in game_state.players:
            if opponent is player:
                continue

            def attack(target):
                if len(target.hand) < 5:
                    return
                hand = list(target.hand)
                pick = max(hand, key=lambda c: (c.cost.coins, c.is_action, c.name))
                if pick in target.hand:
                    target.hand.remove(pick)
                    game_state.discard_card(target, pick)

            game_state.attack_player(opponent, attack)


class Specialist(Card):
    """$5 Action-Liaison. You may play an Action from hand. Then choose:
    play it again; or gain a copy of it. +1 Favor."""

    def __init__(self):
        super().__init__(
            name="Specialist",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.LIAISON],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        player.favors += 1

        actions = [c for c in player.hand if c.is_action]
        if not actions:
            return
        choice = player.ai.choose_action(game_state, actions + [None])
        if choice is None or choice not in player.hand:
            return
        player.hand.remove(choice)
        player.in_play.append(choice)
        choice.on_play(game_state)

        # Choose: play again, or gain a copy.
        # Heuristic: gain a copy of cheap cantrips ($3-$5); replay otherwise.
        if (
            choice.cost.coins <= 5
            and game_state.supply.get(choice.name, 0) > 0
        ):
            try:
                copy = get_card(choice.name)
            except ValueError:
                copy = None
            if copy is not None:
                game_state.supply[choice.name] -= 1
                game_state.gain_card(player, copy)
                return
        choice.on_play(game_state)


class Swap(Card):
    """$5 Action-Liaison. +1 Card +1 Action. You may return an Action from
    hand to its pile to gain a different non-duplicate Action costing
    exactly the returned card's cost +1. +1 Favor."""

    def __init__(self):
        super().__init__(
            name="Swap",
            cost=CardCost(coins=5),
            stats=CardStats(actions=1, cards=1),
            types=[CardType.ACTION, CardType.LIAISON],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        player.favors += 1

        actions_in_hand = [
            c for c in player.hand
            if c.is_action and game_state.supply.get(c.name, 0) is not None
        ]
        if not actions_in_hand:
            return
        # Choose to return the worst Action with a useful upgrade target.
        candidates: list[tuple[Card, Card]] = []
        for src in actions_in_hand:
            target_cost = src.cost.coins + 1
            for name, count in game_state.supply.items():
                if count <= 0 or name == src.name:
                    continue
                try:
                    target = get_card(name)
                except ValueError:
                    continue
                if not target.is_action:
                    continue
                if target.cost.coins != target_cost:
                    continue
                if target.cost.potions > 0:
                    continue
                if not target.may_be_bought(game_state):
                    continue
                candidates.append((src, target))
                break
        if not candidates:
            return
        # Pick the trade with the cheapest source that yields a target.
        src, target = min(candidates, key=lambda pair: (pair[0].cost.coins, pair[0].name))
        if src not in player.hand:
            return
        player.hand.remove(src)
        # Return src to its pile.
        if src.name in game_state.supply:
            game_state.supply[src.name] = game_state.supply.get(src.name, 0) + 1
        # Gain target.
        if game_state.supply.get(target.name, 0) <= 0:
            return
        game_state.supply[target.name] -= 1
        game_state.gain_card(player, target)

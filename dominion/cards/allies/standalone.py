"""Standalone Allies expansion kingdom cards (non-split).

Bauble, Sycophant, Importer, Contract, Emissary, Galleria, Hunter,
Skirmisher, Specialist, Swap, Underling, Broker, Capital City, Carpenter,
Courier, Guildmaster, Innkeeper, Marquis, Merchant Camp, Royal Galley,
Sentinel, Town.
"""

from typing import Optional

from ..base_card import Card, CardCost, CardStats, CardType


# ---------------------------------------------------------------------------
# $2 Liaisons
# ---------------------------------------------------------------------------

class Bauble(Card):
    """$2 Treasure-Liaison. Choose two different options: +1 Buy; +$1;
    +1 Favor; or this turn when you gain a card, you may put it onto your
    deck. Simulator default picks +1 Buy and +$1; AIs may implement
    choose_bauble_options to pick any two printed options.
    """

    def __init__(self):
        super().__init__(
            name="Bauble",
            cost=CardCost(coins=2),
            stats=CardStats(),
            types=[CardType.TREASURE, CardType.LIAISON],
        )

    def on_play(self, game_state):
        from dominion.ways.chameleon import chameleon_plus_coins

        player = game_state.current_player
        options = ("buy", "coin", "favor", "topdeck")
        chooser = getattr(player.ai, "choose_bauble_options", None)
        if chooser is None:
            chosen = ["buy", "coin"]
        else:
            chosen = chooser(game_state, player, list(options), 2)

        selected: list[str] = []
        for option in chosen or []:
            if option in options and option not in selected:
                selected.append(option)
            if len(selected) == 2:
                break
        for option in ("buy", "coin"):
            if len(selected) == 2:
                break
            if option not in selected:
                selected.append(option)

        for option in selected:
            if option == "buy":
                player.buys += 1
            elif option == "coin":
                chameleon_plus_coins(player, 1)
            elif option == "favor":
                player.favors += 1
            elif option == "topdeck":
                player.topdeck_gains = True


class Sycophant(Card):
    """$2 Action-Liaison. +1 Action. Discard 3 cards. When you gain or
    trash this, +2 Favors.
    """

    def __init__(self):
        super().__init__(
            name="Sycophant",
            cost=CardCost(coins=2),
            stats=CardStats(actions=1),
            types=[CardType.ACTION, CardType.LIAISON],
        )

    def play_effect(self, game_state):
        from dominion.ways.chameleon import chameleon_plus_coins

        player = game_state.current_player
        if not player.hand:
            return
        discard_count = min(3, len(player.hand))
        picks = player.ai.choose_cards_to_discard(
            game_state, player, list(player.hand), discard_count, reason="sycophant"
        )
        selected: list[Card] = []
        for card in picks or []:
            if card in player.hand and card not in selected:
                selected.append(card)
            if len(selected) == discard_count:
                break
        for card in list(player.hand):
            if len(selected) == discard_count:
                break
            if card not in selected:
                selected.append(card)

        discarded = 0
        for card in selected:
            if card in player.hand:
                player.hand.remove(card)
                game_state.discard_card(player, card)
                discarded += 1
        if discarded:
            chameleon_plus_coins(player, 3)

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)
        player.favors += 2

    def on_trash(self, game_state, player):
        super().on_trash(game_state, player)
        player.favors += 2


# ---------------------------------------------------------------------------
# $3 Liaisons
# ---------------------------------------------------------------------------

class Importer(Card):
    """$3 Action-Duration-Liaison. At start of next turn, gain a card
    costing up to $5. Setup: each player starts with 5 Favors instead of
    1; Importer does not grant any Favors on play."""

    def __init__(self):
        super().__init__(
            name="Importer",
            cost=CardCost(coins=3),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.DURATION, CardType.LIAISON],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
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
            game_state.play_action_indirectly(
                player, top, blocked_return_zone=player.discard
            )
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
    """$4 Action-Duration. +1 Card. You may play a non-Duration Action
    from hand. Set it aside; if you did, play it at the start of your next
    turn.
    """

    def __init__(self):
        super().__init__(
            name="Royal Galley",
            cost=CardCost(coins=4),
            stats=CardStats(cards=1),
            types=[CardType.ACTION, CardType.DURATION],
        )
        self._set_aside: Optional[Card] = None

    def play_effect(self, game_state):
        player = game_state.current_player
        self._set_aside = None
        actions = [
            c for c in player.hand
            if c.is_action and not c.is_duration
        ]
        if not actions:
            return
        choice = player.ai.choose_action(game_state, actions + [None])
        if choice is None or choice not in player.hand:
            return
        if not game_state.move_card_from_hand_to_play(player, choice):
            return
        game_state.play_action_indirectly(player, choice)
        if choice not in player.in_play:
            return
        player.in_play.remove(choice)
        self._set_aside = choice
        self.duration_persistent = False
        if self not in player.duration:
            player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        if self in player.in_play:
            player.in_play.remove(self)
        if self._set_aside is None:
            return
        card = self._set_aside
        self._set_aside = None
        player.in_play.append(card)
        game_state.play_action_indirectly(player, card, blocked_return_zone=player.discard)
        self.duration_persistent = False


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
    """$5 Treasure-Duration-Liaison. +$2. You may set aside an Action from
    your hand; if you do, play it at the start of your next turn.

    Per official Allies rules, Contract does not grant +1 Favor on play.
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
        from dominion.ways.chameleon import chameleon_plus_coins

        player = game_state.current_player
        chameleon_plus_coins(player, 2)

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
        game_state.play_action_indirectly(player, card, blocked_return_zone=player.discard)


class Emissary(Card):
    """$5 Action-Liaison. +3 Cards. If drawing those cards caused you to
    shuffle (i.e. you had at least one card in your discard pile when the
    +3 Cards resolved), +1 Action and +2 Favors.
    """

    def __init__(self):
        super().__init__(
            name="Emissary",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.LIAISON],
        )

    def play_effect(self, game_state):
        from dominion.ways.chameleon import chameleon_plus_cards

        player = game_state.current_player
        will_shuffle = len(player.deck) < 3 and bool(player.discard)
        chameleon_plus_cards(game_state, player, 3)
        if will_shuffle and not getattr(self, "_chameleon_active", False):
            if not player.ignore_action_bonuses:
                player.actions += 1
            player.favors += 2


class Galleria(Card):
    """$5 Action-Liaison. +$3. This turn, when you gain a card costing $3
    or more, +1 Buy.

    Per official Allies rules, Galleria does not grant +1 Favor on play.
    """

    def __init__(self):
        super().__init__(
            name="Galleria",
            cost=CardCost(coins=5),
            stats=CardStats(coins=3),
            types=[CardType.ACTION, CardType.LIAISON],
        )

    def on_owner_gain(self, game_state, player, gained_card: Card) -> None:
        if gained_card.cost.coins >= 3:
            player.buys += 1


class Hunter(Card):
    """$5 Action-Liaison. +1 Action. Reveal top 3 cards; put one Action,
    one Treasure, one Victory into hand; discard the rest."""

    def __init__(self):
        super().__init__(
            name="Hunter",
            cost=CardCost(coins=5),
            stats=CardStats(actions=1),
            types=[CardType.ACTION, CardType.LIAISON],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

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
    """$5 Action-Liaison. You may play an Action or Treasure card from your
    hand. If you did, choose: play it again; or gain a copy of it.

    Per official Allies rules, Specialist does not grant +1 Favor on play.
    """

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

        actions = [c for c in player.hand if c.is_action]
        if not actions:
            return
        choice = player.ai.choose_action(game_state, actions + [None])
        if choice is None or choice not in player.hand:
            return
        if not game_state.move_card_from_hand_to_play(player, choice):
            return
        game_state.play_action_indirectly(player, choice)

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
        game_state.play_action_indirectly(player, choice)


class Swap(Card):
    """$5 Action-Liaison. +1 Card, +1 Action. You may return an Action card
    from your hand to its pile; if you do, gain an Action card from the
    Supply costing up to $5 (not the same name as the returned card), and
    put it into your hand.

    Per official Allies rules, Swap does not grant +1 Favor on play.
    """

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


# ---------------------------------------------------------------------------
# $3 standalone
# ---------------------------------------------------------------------------

class MerchantCamp(Card):
    """$3 Action. +2 Actions +$1. When you discard this card from play, you
    may put it onto your deck.

    Implementation: always topdeck. Merchant Camp is a non-drawing village,
    so saving it for next turn (or the next draw) dominates leaving it in
    the discard. The "when you discard from play" trigger is independent of
    how the card was played, so cleanup honours it by name (like Walled
    Village) — this matters when Merchant Camp is played via a Way (which
    bypasses ``play_effect``) or under Enchantress (whose effect replaces
    ``on_play`` entirely).
    """

    def __init__(self):
        super().__init__(
            name="Merchant Camp",
            cost=CardCost(coins=3),
            stats=CardStats(actions=2, coins=1),
            types=[CardType.ACTION],
        )


class Sentinel(Card):
    """$3 Action. Look at the top 5 cards of your deck. Trash up to 2 of
    them. Put the rest back on top in any order."""

    def __init__(self):
        super().__init__(
            name="Sentinel",
            cost=CardCost(coins=3),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        revealed: list[Card] = []
        for _ in range(5):
            if not player.deck and player.discard:
                player.shuffle_discard_into_deck()
            if not player.deck:
                break
            revealed.append(player.deck.pop())

        # Trash up to 2 of the worst cards seen.
        trash_priority = {
            "Curse": 0,
            "Overgrown Estate": 1,
            "Ruined Village": 2,
            "Ruined Market": 2,
            "Ruined Library": 2,
            "Survivors": 2,
            "Abandoned Mine": 2,
            "Estate": 3,
            "Hovel": 4,
            "Copper": 5,
        }
        candidates = [c for c in revealed if c.name in trash_priority]
        candidates.sort(key=lambda c: (trash_priority[c.name], c.name))
        for card in candidates[:2]:
            revealed.remove(card)
            game_state.trash_card(player, card)

        # Put the rest back on top of the deck. ``deck.pop()`` takes from
        # the end, so the last appended card is the next one drawn. Sort
        # so Victory clutter sinks to the bottom (appended first → low
        # index → drawn last) and the highest-cost non-Victory ends up on
        # top (appended last → drawn first).
        revealed.sort(key=lambda c: (not c.is_victory, c.cost.coins))
        for card in revealed:
            player.deck.append(card)


# ---------------------------------------------------------------------------
# $5 standalone
# ---------------------------------------------------------------------------

class CapitalCity(Card):
    """$5 Action. +1 Card +2 Actions. You may discard 2 cards for +$2. You
    may pay $2 for +2 Cards."""

    def __init__(self):
        super().__init__(
            name="Capital City",
            cost=CardCost(coins=5),
            stats=CardStats(actions=2, cards=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        hand_size_before = len(player.hand)

        # Option 1: discard 2 for +$2. Take it when there are at least two
        # low-value cards we'd rather not see this turn.
        junk_names = {
            "Curse", "Estate", "Copper", "Hovel", "Overgrown Estate",
            "Ruined Village", "Ruined Market", "Ruined Library",
            "Survivors", "Abandoned Mine", "Necropolis",
        }
        junk = [c for c in player.hand if c.name in junk_names]
        if len(junk) >= 2:
            picks = player.ai.choose_cards_to_discard(
                game_state, player, list(player.hand), 2, reason="capital_city"
            )
            discarded = 0
            for card in picks[:2]:
                if card in player.hand:
                    player.hand.remove(card)
                    game_state.discard_card(player, card)
                    discarded += 1
            if discarded == 2:
                player.coins += 2

        # Option 2: pay $2 for +2 Cards. Take it when the hand was short
        # entering the play — paying $2 to refill is worth it. We gate on
        # the pre-play hand size so that "discard 2 for +$2" doesn't make
        # the hand artificially small and immediately drain those coins.
        if player.coins >= 2 and hand_size_before <= 2:
            player.coins -= 2
            game_state.draw_cards(player, 2)


class Guildmaster(Card):
    """$5 Action-Liaison. +$3. This turn, when you gain a card, +1 Favor.

    Terminal — Guildmaster does not give +1 Action despite being a Liaison.
    """

    def __init__(self):
        super().__init__(
            name="Guildmaster",
            cost=CardCost(coins=5),
            stats=CardStats(coins=3),
            types=[CardType.ACTION, CardType.LIAISON],
        )

    def on_owner_gain(self, game_state, player, gained_card: Card) -> None:
        player.favors += 1


# ---------------------------------------------------------------------------
# $6 standalone
# ---------------------------------------------------------------------------

class Marquis(Card):
    """$6 Action. +1 Buy. +1 Card per card in your hand. Then discard down
    to 10 cards in hand."""

    def __init__(self):
        super().__init__(
            name="Marquis",
            cost=CardCost(coins=6),
            stats=CardStats(buys=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        n = len(player.hand)
        if n > 0:
            game_state.draw_cards(player, n)
        excess = max(0, len(player.hand) - 10)
        if excess > 0:
            picks = player.ai.choose_cards_to_discard(
                game_state, player, list(player.hand), excess, reason="marquis"
            )
            for card in picks[:excess]:
                if card in player.hand:
                    player.hand.remove(card)
                    game_state.discard_card(player, card)

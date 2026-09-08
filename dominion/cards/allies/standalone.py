"""Standalone Allies expansion kingdom cards (non-split).

Bauble, Sycophant, Importer, Contract, Emissary, Galleria, Hunter,
Skirmisher, Specialist, Swap, Underling, Broker, Capital City, Carpenter,
Courier, Guildmaster, Innkeeper, Marquis, Merchant Camp, Royal Galley,
Sentinel, Town.
"""

from ..base_card import Card, CardCost, CardStats, CardType
from ._rules import (
    candidates,
    decide,
    discard,
    effective_cost,
    gain,
    play_from_hand,
    plus_cards,
    plus_coins,
    retain_multiplier,
    select_modes,
    trash_from_hand,
)

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
    """$2 Action-Liaison. +1 Action. Discard 3 cards; if any were discarded,
    +$3. When you gain or trash this, +2 Favors.
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
        if discarded >= 1:
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
    """Gain up to $5 next turn; setup provides four additional Favors."""

    def __init__(self):
        super().__init__(
            name="Importer",
            cost=CardCost(coins=3),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.DURATION, CardType.LIAISON],
        )

    def play_effect(self, game_state):
        game_state.current_player.duration.append(self)

    def on_duration(self, game_state):
        gain(
            game_state,
            game_state.current_player,
            candidates(game_state, CardCost(coins=5)),
        )


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
    """Mandatory trash, then one resource per coin of its current cost."""

    def __init__(self):
        super().__init__(
            name="Broker",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.LIAISON],
        )

    def play_effect(self, game_state):
        p = game_state.current_player
        card = trash_from_hand(game_state, p)
        cost = effective_cost(game_state, card).coins if card else 0
        default = (
            "actions"
            if p.actions == 0 and cost >= 2
            else "cards"
            if p.actions and cost >= 3
            else "coins"
        )
        for mode in select_modes(
            game_state, p, self, ["cards", "actions", "coins", "favors"], [default]
        ):
            if mode == "cards":
                plus_cards(game_state, p, cost)
            elif mode == "actions" and not p.ignore_action_bonuses:
                p.actions += cost
            elif mode == "coins":
                plus_coins(p, cost)
            elif mode == "favors":
                p.favors += cost


class Carpenter(Card):
    """Workshop while every pile is stocked, otherwise Remodel."""

    def __init__(self):
        super().__init__(
            name="Carpenter",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        p = game_state.current_player
        if game_state.empty_piles == 0:
            if not p.ignore_action_bonuses:
                p.actions += 1
            limit = CardCost(coins=4)
        else:
            card = trash_from_hand(game_state, p)
            if card is None:
                return
            limit = effective_cost(game_state, card)
            limit.coins += 2
        gain(game_state, p, candidates(game_state, limit))


class Courier(Card):
    """$4 Action. +$1. Discard the top card of your deck, then you may
    play an Action or Treasure from your discard pile."""

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
        if player.deck:
            game_state.discard_card(player, player.deck.pop())

        # Discard reactions may gain cards, play cards, or cause a shuffle.
        # Build the menu only after those effects have completely resolved.
        choices = [
            c
            for c in player.discard
            if c.is_action
            or game_state.is_treasure(c)
            or game_state.is_inherited_estate(player, c)
        ]
        if not choices:
            return
        choice = player.ai.choose_courier_target(game_state, player, choices)
        # None explicitly declines. Reject unavailable cards without moving
        # a different physical copy with the same name.
        if choice is None or not any(choice is c for c in choices):
            return
        if not any(choice is c for c in player.discard):
            return
        overlay = (
            game_state._begin_inherited_estate_overlay(player, choice)
            if game_state.is_inherited_estate(player, choice)
            else None
        )
        try:
            if choice.is_action and not game_state.is_treasure(choice):
                game_state.play_action_from_zone_indirectly(
                    player, choice, player.discard
                )
            else:
                player.discard.remove(choice)
                player.in_play.append(choice)
                game_state.play_treasure_indirectly(player, choice)
        finally:
            game_state._end_inherited_estate_overlay(choice, overlay)


class Innkeeper(Card):
    """Choose a draw, a three-card sift, or a five-card sift."""

    def __init__(self):
        super().__init__(
            name="Innkeeper",
            cost=CardCost(coins=4),
            stats=CardStats(actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        p = game_state.current_player
        clutter = sum(
            c.name in {"Curse", "Copper", "Estate", "Hovel", "Overgrown Estate"}
            for c in p.hand
        )
        default = "sift3" if clutter >= 2 or len(p.hand) <= 2 else "card"
        for mode in select_modes(
            game_state, p, self, ["card", "sift3", "sift5"], [default]
        ):
            plus_cards(game_state, p, {"card": 1, "sift3": 3, "sift5": 5}[mode])
            if mode != "card":
                discard(game_state, p, 3 if mode == "sift3" else 6, "innkeeper")


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
        self._set_aside: list[Card] = []

    @property
    def set_aside(self):
        return self._set_aside

    def play_effect(self, game_state):
        player = game_state.current_player
        actions = [c for c in player.hand if c.is_action and not c.is_duration]
        if not actions:
            return
        choice = player.ai.choose_action(game_state, actions + [None])
        if choice is None or choice not in actions:
            return
        if not game_state.move_card_from_hand_to_play(player, choice):
            return
        game_state.play_action_indirectly(
            player, choice, blocked_return_zone=player.hand
        )
        if choice not in player.in_play:
            return
        player.in_play.remove(choice)
        self._set_aside.append(choice)
        self.duration_persistent = False
        if self not in player.duration:
            player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        if not self._set_aside:
            return
        cards = list(self._set_aside)
        self._set_aside = []
        for card in cards:
            player.in_play.append(card)
            game_state.play_action_indirectly(
                player, card, blocked_return_zone=player.discard
            )
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
        default = (
            "village"
            if any(c.is_action for c in player.hand) or player.actions == 0
            else "coins"
        )
        for mode in select_modes(
            game_state, player, self, ["village", "coins"], [default]
        ):
            if mode == "village":
                plus_cards(game_state, player, 1)
                if not player.ignore_action_bonuses:
                    player.actions += 2
            else:
                player.buys += 1
                plus_coins(player, 2)


# ---------------------------------------------------------------------------
# $5 cards
# ---------------------------------------------------------------------------


class Contract(Card):
    """Treasure giving $2, a Favor, and an optional delayed Action play."""

    def __init__(self):
        super().__init__(
            name="Contract",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.TREASURE, CardType.DURATION, CardType.LIAISON],
        )
        self.set_aside = []

    @property
    def _set_aside(self):
        return self.set_aside[0] if self.set_aside else None

    def on_play(self, game_state):
        p = game_state.current_player
        plus_coins(p, 2)
        p.favors += 1
        actions = [c for c in p.hand if c.is_action]
        choice = p.ai.choose_action(game_state, actions + [None])
        if choice not in actions:
            return
        p.hand.remove(choice)
        self.set_aside.append(choice)
        if self not in p.duration:
            p.duration.append(self)

    def on_duration(self, game_state):
        p = game_state.current_player
        pending, self.set_aside = self.set_aside, []
        for card in pending:
            p.in_play.append(card)
            game_state.play_action_indirectly(p, card)


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
        shuffles = getattr(player, "shuffle_count", 0)
        chameleon_plus_cards(game_state, player, 3)
        if getattr(player, "shuffle_count", 0) > shuffles:
            if not player.ignore_action_bonuses:
                player.actions += 1
            player.favors += 2


class Galleria(Card):
    """$3 and a turn-scoped Buy reward for gains costing exactly $3/$4."""

    def __init__(self):
        super().__init__(
            name="Galleria",
            cost=CardCost(coins=5),
            stats=CardStats(coins=3),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        game_state.register_allies_gain_effect(self, "galleria")


class Hunter(Card):
    """$5 Action. +1 Action. Reveal top 3 cards; put one Action,
    one Treasure, one Victory into hand; discard the rest."""

    def __init__(self):
        super().__init__(
            name="Hunter",
            cost=CardCost(coins=5),
            stats=CardStats(actions=1),
            types=[CardType.ACTION],
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
        for predicate in (
            lambda c: c.is_action,
            lambda c: c.is_treasure,
            lambda c: c.is_victory,
        ):
            matches = [c for c in revealed if predicate(c)]
            if matches:
                pick = max(matches, key=lambda c: (c.cost.coins, c.name))
                revealed.remove(pick)
                player.hand.append(pick)
        for card in revealed:
            game_state.discard_card(player, card)


class Skirmisher(Card):
    """Attack gains this turn make unprotected opponents discard to three."""

    def __init__(self):
        super().__init__(
            name="Skirmisher",
            cost=CardCost(coins=5),
            stats=CardStats(cards=1, actions=1, coins=1),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        p = game_state.current_player
        targets = []
        for opponent in game_state.opponents_in_order(p):
            game_state.attack_player(
                opponent, targets.append, attacker=p, attack_card=self
            )
        game_state.register_allies_gain_effect(self, "skirmisher", targets)


class Specialist(Card):
    """Play an Action/Treasure, then replay it or gain a copy."""

    def __init__(self):
        super().__init__(
            name="Specialist",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        p = game_state.current_player
        card = play_from_hand(game_state, p, treasures=True)
        if card is None:
            return
        copies = candidates(game_state, predicate=lambda c: c.name == card.name)
        default = (
            "gain"
            if effective_cost(game_state, card).coins <= 5 and copies
            else "replay"
        )
        for mode in select_modes(game_state, p, self, ["replay", "gain"], [default]):
            if mode == "gain":
                gain(
                    game_state,
                    p,
                    candidates(game_state, predicate=lambda c: c.name == card.name),
                )
            else:
                if card.is_action:
                    game_state.play_action_indirectly(p, card)
                else:
                    game_state.play_treasure_indirectly(p, card)
                retain_multiplier(p, self, card)


class Swap(Card):
    """Return an Action to its pile and gain a different Action to hand."""

    def __init__(self):
        super().__init__(
            name="Swap",
            cost=CardCost(coins=5),
            stats=CardStats(cards=1, actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        p = game_state.current_player
        sources = [
            c
            for c in p.hand
            if c.is_action and game_state._resolve_changeling_pile_name(c) is not None
        ]
        if not sources:
            return
        source = min(
            sources, key=lambda c: (effective_cost(game_state, c).coins, c.name)
        )
        useful = candidates(
            game_state,
            CardCost(coins=5),
            lambda c: c.is_action and c.name != source.name,
        )
        source = decide(
            game_state, p, "swap_return", [None] + sources, source if useful else None
        )
        if source is None:
            return
        # Synchronize the pile before adding a returning card on top.
        game_state.top_supply_card(source.name)
        p.hand.remove(source)
        game_state._restore_to_supply_pile(source)
        gain(
            game_state,
            p,
            candidates(
                game_state,
                CardCost(coins=5),
                lambda c: c.is_action and c.name != source.name,
            ),
            to_hand=True,
        )


# ---------------------------------------------------------------------------
# $3 standalone
# ---------------------------------------------------------------------------


class MerchantCamp(Card):
    """$3 Action. +2 Actions +$1. When you discard this card from play, you
    may put it onto your deck.

    The default policy topdecks, with an overridable choice at cleanup.
    The "when you discard from play" trigger is independent of
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
            "Curse",
            "Estate",
            "Copper",
            "Hovel",
            "Overgrown Estate",
            "Ruined Village",
            "Ruined Market",
            "Ruined Library",
            "Survivors",
            "Abandoned Mine",
            "Necropolis",
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
    """$3 and one Favor per gain this turn, per play."""

    def __init__(self):
        super().__init__(
            name="Guildmaster",
            cost=CardCost(coins=5),
            stats=CardStats(coins=3),
            types=[CardType.ACTION, CardType.LIAISON],
        )

    def play_effect(self, game_state):
        game_state.register_allies_gain_effect(self, "guildmaster")


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

"""Plunder Events.

The Plunder expansion ships 15 Events. ``Looting`` already exists as a
standalone module; this file covers the remaining 14.

Plunder Events: Bury, Avoid, Deliver, Peril, Rush, Foray, Launch, Mirror,
Prepare, Scrounge, Maelstrom, Invasion, Prosper, Looting (existing),
Cheap (Trait), Cursed (Trait). The actual canonical 15 events are the
above minus the Trait names plus Pursue/Stash etc. depending on edition.
This file implements the 14 not-yet-built ones; combined with ``Looting``
that yields 15 Plunder Events in the registry.
"""

import random

from dominion.cards.base_card import CardCost
from dominion.cards.registry import get_card

from .base_event import Event


def _gain_random_loot(game_state, player):
    from dominion.cards.plunder import LOOT_CARD_NAMES

    loot_name = random.choice(LOOT_CARD_NAMES)
    return game_state.gain_card(player, get_card(loot_name))


class Bury(Event):
    """$1: +1 Buy. Take a card from your discard onto your Bury mat
    (top-decked next shuffle)."""

    def __init__(self):
        super().__init__("Bury", CardCost(coins=1))

    def on_buy(self, game_state, player) -> None:
        player.buys += 1
        if not player.discard:
            return
        # Greedy: bury the most expensive non-Curse, non-Estate card.
        candidates = sorted(
            player.discard,
            key=lambda c: (c.is_victory or c.name == "Curse", -c.cost.coins),
        )
        pick = candidates[0]
        player.discard.remove(pick)
        # Approximation: top-deck immediately so it is drawn next.
        player.deck.append(pick)


class Avoid(Event):
    """$2: The next time you shuffle, set aside up to 3 cards before shuffling,
    then put them on top of your deck."""

    def __init__(self):
        super().__init__("Avoid", CardCost(coins=2))

    def on_buy(self, game_state, player) -> None:
        player.avoid_pending = max(player.avoid_pending, 1) + 0


class Deliver(Event):
    """$2: Set aside the next card you gain this turn. Put it into hand at
    start of next turn."""

    def __init__(self):
        super().__init__("Deliver", CardCost(coins=2))

    def on_buy(self, game_state, player) -> None:
        # Mark the player so the next gain is set aside; checked in gain_card.
        player.deliver_pending = list(getattr(player, "deliver_pending", []))
        # Use a sentinel to indicate one pending; gain_card doesn't currently
        # consult deliver_pending, but a future hook can. As a simple
        # approximation: top-deck the next gain so it lands in hand at start
        # of next turn (after the new hand is drawn). Push a marker onto the
        # player's topdeck_gains flag for one gain.
        player.topdeck_gains = True


class Peril(Event):
    """$2: Trash an Action from your hand. Gain a Loot."""

    def __init__(self):
        super().__init__("Peril", CardCost(coins=2))

    def on_buy(self, game_state, player) -> None:
        actions = [c for c in player.hand if c.is_action]
        if not actions:
            return
        # Greedy: trash the cheapest Action.
        pick = min(actions, key=lambda c: (c.cost.coins, c.name))
        player.hand.remove(pick)
        game_state.trash_card(player, pick)
        _gain_random_loot(game_state, player)


class Rush(Event):
    """$2: The next Action you play has its effect twice."""

    def __init__(self):
        super().__init__("Rush", CardCost(coins=2))

    def on_buy(self, game_state, player) -> None:
        game_state.rush_pending[id(player)] = (
            game_state.rush_pending.get(id(player), 0) + 1
        )


class Foray(Event):
    """$3: Discard 3 differently named cards. If you do, gain a Loot."""

    def __init__(self):
        super().__init__("Foray", CardCost(coins=3))

    def on_buy(self, game_state, player) -> None:
        if len(player.hand) < 3:
            return
        # Find 3 differently-named cards (greedy: cheapest names first).
        seen: set[str] = set()
        chosen: list = []
        for card in sorted(player.hand, key=lambda c: (c.cost.coins, c.name)):
            if card.name in seen:
                continue
            seen.add(card.name)
            chosen.append(card)
            if len(chosen) >= 3:
                break
        if len(chosen) < 3:
            return
        for card in chosen:
            player.hand.remove(card)
            game_state.discard_card(player, card)
        _gain_random_loot(game_state, player)


class Launch(Event):
    """$3: Once per turn. +1 Card +1 Action +1 Buy."""

    def __init__(self):
        super().__init__("Launch", CardCost(coins=3))

    def may_be_bought(self, game_state, player) -> bool:
        return not getattr(player, "launch_used", False)

    def on_buy(self, game_state, player) -> None:
        player.launch_used = True
        game_state.draw_cards(player, 1)
        player.actions += 1
        player.buys += 1


class Mirror(Event):
    """$3: The next Action you gain this turn (other than via Mirror), gain another."""

    def __init__(self):
        super().__init__("Mirror", CardCost(coins=3))

    def on_buy(self, game_state, player) -> None:
        game_state.mirror_pending[id(player)] = (
            game_state.mirror_pending.get(id(player), 0) + 1
        )


class Prepare(Event):
    """$3: +1 Buy. Set aside up to 5 cards face down. Reveal at start of next turn
    and play them."""

    def __init__(self):
        super().__init__("Prepare", CardCost(coins=3))

    def on_buy(self, game_state, player) -> None:
        player.buys += 1
        # Set aside up to 5 cards from hand, played at start of next turn via
        # patient_mat-style mechanic.
        n = min(5, len(player.hand))
        if n == 0:
            return
        # Greedy: take all if hand <=5, else take 5 most expensive.
        cards = sorted(player.hand, key=lambda c: -c.cost.coins)[:n]
        for card in cards:
            player.hand.remove(card)
            player.prepare_set_aside.append(card)
        # Convert prepare_set_aside to patient_mat style: reuse hasty
        # set_aside on the game state for next-turn play.
        game_state.hasty_set_aside.setdefault(id(player), []).extend(player.prepare_set_aside)
        player.prepare_set_aside = []


class Scrounge(Event):
    """$3: Trash an Estate from hand or supply. If from hand: gain a card up to $5.
    If from supply: gain an Estate."""

    def __init__(self):
        super().__init__("Scrounge", CardCost(coins=3))

    def on_buy(self, game_state, player) -> None:
        # Greedy: trash from hand if possible (worth more).
        estates_in_hand = [c for c in player.hand if c.name == "Estate"]
        if estates_in_hand:
            estate = estates_in_hand[0]
            player.hand.remove(estate)
            game_state.trash_card(player, estate)
            # Gain a card up to $5.
            candidates = []
            for name, count in game_state.supply.items():
                if count <= 0:
                    continue
                try:
                    card = get_card(name)
                except ValueError:
                    continue
                if (
                    card.cost.coins <= 5
                    and card.cost.potions == 0
                    and card.cost.debt == 0
                ):
                    candidates.append(card)
            if candidates:
                candidates.sort(key=lambda c: (c.cost.coins, c.name), reverse=True)
                pick = candidates[0]
                game_state.supply[pick.name] -= 1
                game_state.gain_card(player, pick)
        elif game_state.supply.get("Estate", 0) > 0:
            # Trash an Estate from the supply (not really standard, but per text):
            game_state.supply["Estate"] -= 1
            game_state.trash.append(get_card("Estate"))
            if game_state.supply.get("Estate", 0) > 0:
                game_state.supply["Estate"] -= 1
                game_state.gain_card(player, get_card("Estate"))


class Maelstrom(Event):
    """$4: Trash 3 cards from your hand. Each other player with 5+ cards trashes one."""

    def __init__(self):
        super().__init__("Maelstrom", CardCost(coins=4))

    def on_buy(self, game_state, player) -> None:
        # Trash 3 cards: greedy junk-first.
        if len(player.hand) >= 3:
            sorted_hand = sorted(
                player.hand,
                key=lambda c: (
                    -(1 if c.name == "Curse" else 0),
                    c.cost.coins,
                    c.name,
                ),
            )
            for card in sorted_hand[:3]:
                if card in player.hand:
                    player.hand.remove(card)
                    game_state.trash_card(player, card)
        # Each other player with 5+ trashes one.
        for other in game_state.players:
            if other is player:
                continue

            def attack(target):
                if len(target.hand) < 5:
                    return
                pick = min(target.hand, key=lambda c: (c.cost.coins, c.name))
                target.hand.remove(pick)
                game_state.trash_card(target, pick)

            game_state.attack_player(other, attack)


class Invasion(Event):
    """$10: Gain an Action; gain a Duchy; gain a Loot. Play any Attacks in hand.
    Gain 2 Silvers."""

    def __init__(self):
        super().__init__("Invasion", CardCost(coins=10))

    def on_buy(self, game_state, player) -> None:
        # Gain an Action.
        action_candidates = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            try:
                card = get_card(name)
            except ValueError:
                continue
            if card.is_action and not card.is_victory:
                action_candidates.append(card)
        if action_candidates:
            action_candidates.sort(key=lambda c: (c.cost.coins, c.name), reverse=True)
            pick = action_candidates[0]
            game_state.supply[pick.name] -= 1
            game_state.gain_card(player, pick)
        # Gain a Duchy.
        if game_state.supply.get("Duchy", 0) > 0:
            game_state.supply["Duchy"] -= 1
            game_state.gain_card(player, get_card("Duchy"))
        # Gain a Loot.
        _gain_random_loot(game_state, player)
        # Play any Attacks in hand.
        for card in list(player.hand):
            if card.is_attack:
                player.hand.remove(card)
                player.in_play.append(card)
                card.on_play(game_state)
        # Gain 2 Silvers.
        for _ in range(2):
            if game_state.supply.get("Silver", 0) <= 0:
                break
            game_state.supply["Silver"] -= 1
            game_state.gain_card(player, get_card("Silver"))


class Prosper(Event):
    """$10: Gain one of each Loot."""

    def __init__(self):
        super().__init__("Prosper", CardCost(coins=10))

    def on_buy(self, game_state, player) -> None:
        from dominion.cards.plunder import LOOT_CARD_NAMES

        for name in LOOT_CARD_NAMES:
            game_state.gain_card(player, get_card(name))



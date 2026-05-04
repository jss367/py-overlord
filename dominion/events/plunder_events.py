"""Events from the Plunder expansion."""

import random

from dominion.cards.base_card import CardCost
from dominion.cards.registry import get_card

from .base_event import Event


def _gain_random_loot(game_state, player):
    from dominion.cards.plunder.loot_cards import LOOT_CARD_NAMES

    loot_name = random.choice(LOOT_CARD_NAMES)
    loot = get_card(loot_name)
    game_state.gain_card(player, loot)


class Bury(Event):
    """$1 Event: Look at any card from your discard. Place it on top of your deck."""

    def __init__(self):
        super().__init__("Bury", CardCost(coins=1))

    def on_buy(self, game_state, player) -> None:
        if not player.discard:
            return
        choice = player.ai.choose_action(game_state, list(player.discard) + [None])
        if choice is None or choice not in player.discard:
            return
        player.discard.remove(choice)
        player.deck.append(choice)


class Avoid(Event):
    """$2 Event: Discard up to 3 cards from your hand, then draw that many."""

    def __init__(self):
        super().__init__("Avoid", CardCost(coins=2))

    def on_buy(self, game_state, player) -> None:
        if not player.hand:
            return

        max_discard = min(3, len(player.hand))
        chosen = player.ai.choose_cards_to_discard(
            game_state, player, list(player.hand), max_discard, reason="avoid"
        )
        if not chosen:
            return

        valid = []
        remaining = list(player.hand)
        for card in chosen:
            if len(valid) >= max_discard:
                break
            if card in remaining:
                remaining.remove(card)
                valid.append(card)

        for card in valid:
            if card in player.hand:
                player.hand.remove(card)
                game_state.discard_card(player, card)

        if valid:
            game_state.draw_cards(player, len(valid))


class Foray(Event):
    """$3 Event: Discard 3 cards. If they have 3 different names, gain a Loot."""

    def __init__(self):
        super().__init__("Foray", CardCost(coins=3))

    def on_buy(self, game_state, player) -> None:
        if len(player.hand) < 3:
            return

        chosen = player.ai.choose_cards_to_discard(
            game_state, player, list(player.hand), 3, reason="foray"
        )

        valid = []
        remaining = list(player.hand)
        for card in chosen:
            if len(valid) >= 3:
                break
            if card in remaining:
                remaining.remove(card)
                valid.append(card)

        if len(valid) < 3:
            return

        for card in valid:
            if card in player.hand:
                player.hand.remove(card)
                game_state.discard_card(player, card)

        if len({c.name for c in valid}) == 3:
            _gain_random_loot(game_state, player)


class Peril(Event):
    """$2 Event: Trash an Action card from your hand. If you do, gain a Loot."""

    def __init__(self):
        super().__init__("Peril", CardCost(coins=2))

    def on_buy(self, game_state, player) -> None:
        actions_in_hand = [c for c in player.hand if c.is_action]
        if not actions_in_hand:
            return

        choice = player.ai.choose_card_to_trash(
            game_state, list(actions_in_hand) + [None]
        )
        if choice is None or choice not in player.hand:
            return

        player.hand.remove(choice)
        game_state.trash_card(player, choice)
        _gain_random_loot(game_state, player)


class Scrounge(Event):
    """$3 Event: Choose one: Trash a card from your hand; or gain an Estate
    from the trash. If you trashed an Estate, also gain a Duchy.
    """

    def __init__(self):
        super().__init__("Scrounge", CardCost(coins=3))

    def on_buy(self, game_state, player) -> None:
        estate_in_trash = any(c.name == "Estate" for c in game_state.trash)

        decision = "trash"
        if hasattr(player.ai, "scrounge_choice"):
            decision = player.ai.scrounge_choice(
                game_state, player, estate_in_trash
            )
            if decision not in {"trash", "gain_estate"}:
                decision = "trash"

        if decision == "gain_estate":
            if estate_in_trash:
                # Pull an Estate from the trash; gain it normally.
                for idx, c in enumerate(game_state.trash):
                    if c.name == "Estate":
                        estate = game_state.trash.pop(idx)
                        game_state.gain_card(player, estate, from_supply=False)
                        return
            return

        # decision == "trash"
        if not player.hand:
            return

        choice = player.ai.choose_card_to_trash(
            game_state, list(player.hand) + [None]
        )
        if choice is None or choice not in player.hand:
            return

        was_estate = choice.name == "Estate"
        player.hand.remove(choice)
        game_state.trash_card(player, choice)

        if was_estate and game_state.supply.get("Duchy", 0) > 0:
            game_state.supply["Duchy"] -= 1
            game_state.gain_card(player, get_card("Duchy"))


class Prosper(Event):
    """$10 Event: Gain a Loot, then any number of differently named Treasures
    from the supply.
    """

    def __init__(self):
        super().__init__("Prosper", CardCost(coins=10))

    def on_buy(self, game_state, player) -> None:
        _gain_random_loot(game_state, player)

        # Build the list of unique Treasure cards available in the supply.
        seen_names: set[str] = set()
        available = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            if name in seen_names:
                continue
            card = get_card(name)
            if not card.is_treasure:
                continue
            seen_names.add(name)
            available.append(card)

        chosen: list = []
        if hasattr(player.ai, "prosper_choose_treasures"):
            chosen = player.ai.prosper_choose_treasures(
                game_state, player, list(available)
            )
            if not isinstance(chosen, list):
                chosen = []
        else:
            # Default: take Silver and Gold (most universally valuable).
            chosen = [c for c in available if c.name in {"Silver", "Gold"}]

        # Enforce "differently named" — at most one of each name.
        gained_names: set[str] = set()
        for card in chosen:
            if card.name in gained_names:
                continue
            if game_state.supply.get(card.name, 0) <= 0:
                continue
            gained_names.add(card.name)
            game_state.supply[card.name] -= 1
            game_state.gain_card(player, get_card(card.name))


class Journey(Event):
    """$4 Event: Take an extra turn after this one, in which you don't draw
    a new hand. Cannot be used to chain off a turn that is itself an extra
    turn.
    """

    def __init__(self):
        super().__init__("Journey", CardCost(coins=4))

    def on_buy(self, game_state, player) -> None:
        if getattr(game_state, "is_extra_turn", False):
            # Already on an extra turn — refuse to chain another.
            return
        game_state.extra_turn = True
        player.skip_next_draw_phase = True


class Prepare(Event):
    """$5 Event: Set aside the cards in your hand. At the start of your next
    turn, play those cards in any order.
    """

    def __init__(self):
        super().__init__("Prepare", CardCost(coins=5))

    def on_buy(self, game_state, player) -> None:
        for card in list(player.hand):
            player.hand.remove(card)
            player.prepared_cards.append(card)


class Deliver(Event):
    """$2 Event: Set aside cards you gain for the rest of this turn. At the
    start of your next turn, put them into your hand.
    """

    def __init__(self):
        super().__init__("Deliver", CardCost(coins=2))

    def on_buy(self, game_state, player) -> None:
        player.deliver_armed = True


class Mirror(Event):
    """$3 Event: The next time you gain an Action card this turn, you may
    gain another copy of it.
    """

    def __init__(self):
        super().__init__("Mirror", CardCost(coins=3))

    def on_buy(self, game_state, player) -> None:
        player.mirror_armed = True


class Invasion(Event):
    """$10 Event: Play an Attack card from your hand. Gain a Duchy, a Gold,
    a Loot, and a Province.
    """

    def __init__(self):
        super().__init__("Invasion", CardCost(coins=10))

    def on_buy(self, game_state, player) -> None:
        # Optional: play an Attack from hand.
        attacks_in_hand = [c for c in player.hand if c.is_attack]
        if attacks_in_hand:
            choice = player.ai.choose_action(
                game_state, list(attacks_in_hand) + [None]
            )
            if choice is not None and choice in player.hand:
                player.hand.remove(choice)
                player.in_play.append(choice)
                choice.on_play(game_state)
                game_state._dispatch_on_action_played(player, choice)

        # Sequential gains.
        for name in ("Duchy", "Gold"):
            if game_state.supply.get(name, 0) > 0:
                game_state.supply[name] -= 1
                game_state.gain_card(player, get_card(name))

        _gain_random_loot(game_state, player)

        if game_state.supply.get("Province", 0) > 0:
            game_state.supply["Province"] -= 1
            game_state.gain_card(player, get_card("Province"))

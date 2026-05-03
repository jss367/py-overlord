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
    """$4 Event: Trash an Estate from your hand to gain a Gold. Otherwise,
    gain an Estate.
    """

    def __init__(self):
        super().__init__("Scrounge", CardCost(coins=4))

    def on_buy(self, game_state, player) -> None:
        estate_in_hand = next(
            (c for c in player.hand if c.name == "Estate"), None
        )

        if estate_in_hand is not None:
            player.hand.remove(estate_in_hand)
            game_state.trash_card(player, estate_in_hand)
            if game_state.supply.get("Gold", 0) > 0:
                game_state.supply["Gold"] -= 1
                game_state.gain_card(player, get_card("Gold"))
            return

        if game_state.supply.get("Estate", 0) > 0:
            game_state.supply["Estate"] -= 1
            game_state.gain_card(player, get_card("Estate"))


class Prosper(Event):
    """$10 Event: Gain a Loot and one Treasure of each cost up through Gold."""

    def __init__(self):
        super().__init__("Prosper", CardCost(coins=10))

    def on_buy(self, game_state, player) -> None:
        _gain_random_loot(game_state, player)
        for name in ("Silver", "Gold"):
            if game_state.supply.get(name, 0) > 0:
                game_state.supply[name] -= 1
                game_state.gain_card(player, get_card(name))


class Journey(Event):
    """$4 Event: Take an extra turn after this one, in which you don't draw
    a new hand.
    """

    def __init__(self):
        super().__init__("Journey", CardCost(coins=4))

    def on_buy(self, game_state, player) -> None:
        game_state.extra_turn = True
        player.skip_next_draw_phase = True


class Prepare(Event):
    """$5 Event: Set aside the cards you have in play and the cards in your
    hand. At the start of your next turn, play those cards in any order.
    """

    def __init__(self):
        super().__init__("Prepare", CardCost(coins=5))

    def on_buy(self, game_state, player) -> None:
        # Move in-play (excluding durations that are still resolving) and hand
        # to the prepared mat. Treat durations as ineligible to set aside so
        # their lingering effects still resolve.
        moveable_in_play = [
            c for c in player.in_play if c not in player.duration
        ]
        for card in moveable_in_play:
            player.in_play.remove(card)
            player.prepared_cards.append(card)

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
    """$10 Event: Gain an Action card. Each other player gains a Curse."""

    def __init__(self):
        super().__init__("Invasion", CardCost(coins=10))

    def on_buy(self, game_state, player) -> None:
        actions_available = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            card = get_card(name)
            if card.is_action and card.cost.potions == 0:
                actions_available.append(card)

        if actions_available:
            actions_available.sort(
                key=lambda c: (c.cost.coins, c.name), reverse=True
            )
            choice = player.ai.choose_buy(
                game_state, list(actions_available) + [None]
            )
            if choice is None or game_state.supply.get(choice.name, 0) <= 0:
                choice = actions_available[0]
            game_state.supply[choice.name] -= 1
            game_state.gain_card(player, choice)

        for other in game_state.players:
            if other is player:
                continue
            game_state.give_curse_to_player(other)

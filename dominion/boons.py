"""Definitions of Dominion Nocturne Boons.

Boons are 12 named good-things drawn from a Boons deck (analogous to the
Hexes deck). A handful of Boons stay with the player until the start of
their next turn (Field's, Forest's, River's). The rest fire-and-discard.
"""

from __future__ import annotations

import random
from typing import Callable, TYPE_CHECKING

from dominion.cards.registry import get_card

if TYPE_CHECKING:  # pragma: no cover - import for type checking only
    from dominion.game.game_state import GameState
    from dominion.game.player_state import PlayerState

BoonEffect = Callable[["GameState", "PlayerState"], None]


# ----- Persistent Boons (kept on the player through their next turn) -----

PERSISTENT_BOONS = {
    "The Field's Gift",
    "The Forest's Gift",
    "The River's Gift",
}


# ----- Individual Boon effects -----


def the_earths_gift(game_state: "GameState", player: "PlayerState") -> None:
    """Discard a Treasure to gain a card costing up to $4."""

    treasures = [card for card in player.hand if card.is_treasure]
    if not treasures:
        return

    # AI hook: should the player discard a Treasure for the gain?
    treasure = player.ai.choose_treasure_to_discard_for_earths_gift(
        game_state, player, treasures
    )
    if treasure is None or treasure not in player.hand:
        return

    player.hand.remove(treasure)
    game_state.discard_card(player, treasure)

    # Choose card to gain costing up to $4
    options = []
    for name, count in game_state.supply.items():
        if count <= 0:
            continue
        try:
            card = get_card(name)
        except ValueError:
            continue
        if card.cost.coins > 4 or card.cost.potions > 0 or card.cost.debt > 0:
            continue
        if not card.may_be_bought(game_state):
            continue
        options.append(card)
    if not options:
        return

    choice = player.ai.choose_card_to_gain_up_to(game_state, player, options, 4)
    if choice is None:
        choice = max(options, key=lambda c: (c.cost.coins, c.name))
    if game_state.supply.get(choice.name, 0) <= 0:
        return
    game_state.supply[choice.name] -= 1
    game_state.gain_card(player, choice)


def the_fields_gift(game_state: "GameState", player: "PlayerState") -> None:
    """+1 Action +$1 (persistent — applied immediately and at start of next turn)."""

    if not player.ignore_action_bonuses:
        player.actions += 1
    player.coins += 1


def the_flames_gift(game_state: "GameState", player: "PlayerState") -> None:
    """Trash a card from your hand."""

    if not player.hand:
        return
    choice = player.ai.choose_card_to_trash(game_state, list(player.hand))
    if choice is None or choice not in player.hand:
        return
    player.hand.remove(choice)
    game_state.trash_card(player, choice)


def the_forests_gift(game_state: "GameState", player: "PlayerState") -> None:
    """+1 Buy +$1 (persistent — also next turn)."""

    player.buys += 1
    player.coins += 1


def the_moons_gift(game_state: "GameState", player: "PlayerState") -> None:
    """Look through your discard, may put a card on top of deck."""

    if not player.discard:
        return
    choice = player.ai.choose_card_to_topdeck_from_discard(
        game_state, player, list(player.discard)
    )
    if choice is None or choice not in player.discard:
        return
    player.discard.remove(choice)
    player.deck.append(choice)


def the_mountains_gift(game_state: "GameState", player: "PlayerState") -> None:
    """Gain a Silver."""

    if game_state.supply.get("Silver", 0) <= 0:
        return
    game_state.supply["Silver"] -= 1
    game_state.gain_card(player, get_card("Silver"))


def the_rivers_gift(game_state: "GameState", player: "PlayerState") -> None:
    """+1 Card at end of turn (persistent — fires during cleanup, before redraw)."""

    # No immediate effect; the +1 Card is delivered by the cleanup hook in
    # GameState which inspects the player's active_boons and increments their
    # cleanup draw count by one per River's Gift active.


def the_seas_gift(game_state: "GameState", player: "PlayerState") -> None:
    """+1 Card."""

    game_state.draw_cards(player, 1)


def the_skys_gift(game_state: "GameState", player: "PlayerState") -> None:
    """Discard 3 cards. If you do, gain a Gold."""

    if len(player.hand) < 3:
        return
    discards = player.ai.choose_cards_to_discard(
        game_state, player, list(player.hand), 3
    )
    if len(discards) < 3:
        return
    for card in discards[:3]:
        if card in player.hand:
            player.hand.remove(card)
            game_state.discard_card(player, card)

    if game_state.supply.get("Gold", 0) > 0:
        game_state.supply["Gold"] -= 1
        game_state.gain_card(player, get_card("Gold"))


def the_suns_gift(game_state: "GameState", player: "PlayerState") -> None:
    """Look at top 4 cards. Discard or put back any."""

    revealed: list = []
    for _ in range(4):
        if not player.deck:
            player.shuffle_discard_into_deck()
        if not player.deck:
            break
        revealed.append(player.deck.pop())

    if not revealed:
        return

    discards = player.ai.choose_cards_to_discard(
        game_state, player, list(revealed), len(revealed)
    )
    discard_set = []
    for card in discards:
        if card in revealed:
            revealed.remove(card)
            discard_set.append(card)

    for card in discard_set:
        game_state.discard_card(player, card)

    # Remaining ``revealed`` go back on top of deck. AI may pick order; default
    # by cost (cheapest first so expensive cards are drawn first).
    ordered = player.ai.order_cards_for_topdeck(game_state, player, list(revealed))
    if not ordered or len(ordered) != len(revealed):
        ordered = sorted(revealed, key=lambda c: (c.cost.coins, c.name))
    for card in ordered:
        player.deck.append(card)


def the_swamps_gift(game_state: "GameState", player: "PlayerState") -> None:
    """Gain a Will-o'-Wisp from its pile."""

    if game_state.supply.get("Will-o'-Wisp", 0) <= 0:
        return
    game_state.supply["Will-o'-Wisp"] -= 1
    game_state.gain_card(player, get_card("Will-o'-Wisp"))


def the_winds_gift(game_state: "GameState", player: "PlayerState") -> None:
    """+2 Cards. Discard 2 cards."""

    game_state.draw_cards(player, 2)
    if not player.hand:
        return
    count = min(2, len(player.hand))
    discards = player.ai.choose_cards_to_discard(
        game_state, player, list(player.hand), count
    )
    for card in discards[:count]:
        if card in player.hand:
            player.hand.remove(card)
            game_state.discard_card(player, card)


BOON_EFFECTS: dict[str, BoonEffect] = {
    "The Earth's Gift": the_earths_gift,
    "The Field's Gift": the_fields_gift,
    "The Flame's Gift": the_flames_gift,
    "The Forest's Gift": the_forests_gift,
    "The Moon's Gift": the_moons_gift,
    "The Mountain's Gift": the_mountains_gift,
    "The River's Gift": the_rivers_gift,
    "The Sea's Gift": the_seas_gift,
    "The Sky's Gift": the_skys_gift,
    "The Sun's Gift": the_suns_gift,
    "The Swamp's Gift": the_swamps_gift,
    "The Wind's Gift": the_winds_gift,
}


def create_boons_deck() -> list[str]:
    """Return a shuffled list of Boon names for a new game."""

    names = list(BOON_EFFECTS.keys())
    random.shuffle(names)
    return names


def resolve_boon(name: str, game_state: "GameState", player: "PlayerState") -> None:
    """Execute the Boon ``name`` for ``player`` if it exists."""

    effect = BOON_EFFECTS.get(name)
    if effect is not None:
        effect(game_state, player)


def is_persistent_boon(name: str) -> bool:
    """Return True if the Boon stays with the player into their next turn."""

    return name in PERSISTENT_BOONS

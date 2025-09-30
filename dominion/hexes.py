"""Definitions of Dominion Hex effects used by Doom cards."""

from __future__ import annotations

import random
from typing import Callable, TYPE_CHECKING

from dominion.cards.registry import get_card

if TYPE_CHECKING:  # pragma: no cover - import for type checking only
    from dominion.game.game_state import GameState
    from dominion.game.player_state import PlayerState

HexEffect = Callable[["GameState", "PlayerState"], None]


def bad_omens(game_state: "GameState", player: "PlayerState") -> None:
    """Move the deck to the discard and topdeck up to two Coppers."""

    if player.deck:
        player.discard.extend(player.deck)
        player.deck.clear()

    coppers = [card for card in player.discard if card.name == "Copper"]
    for _ in range(min(2, len(coppers))):
        copper = coppers.pop()
        if copper in player.discard:
            player.discard.remove(copper)
        player.deck.append(copper)


def delusion(game_state: "GameState", player: "PlayerState") -> None:
    """Give the player the Deluded state if possible."""

    if not player.deluded and not player.envious:
        player.deluded = True


def envy(game_state: "GameState", player: "PlayerState") -> None:
    """Give the player the Envious state if possible."""

    if not player.deluded and not player.envious:
        player.envious = True


def famine(game_state: "GameState", player: "PlayerState") -> None:
    """Reveal three cards, discarding Actions and shuffling the rest back."""

    revealed = []
    for _ in range(3):
        if not player.deck:
            player.shuffle_discard_into_deck()
        if not player.deck:
            break
        revealed.append(player.deck.pop())

    to_keep = []
    for card in revealed:
        if card.is_action:
            game_state.discard_card(player, card)
        else:
            to_keep.append(card)

    random.shuffle(to_keep)
    player.deck.extend(to_keep)


def fear(game_state: "GameState", player: "PlayerState") -> None:
    """Force the player to discard an Action or Treasure if possible."""

    if len(player.hand) < 5:
        return

    choices = [card for card in player.hand if card.is_action or card.is_treasure]
    if not choices:
        return

    selected = player.ai.choose_cards_to_discard(game_state, player, choices, 1)
    card = selected[0] if selected else choices[0]
    if card in player.hand:
        player.hand.remove(card)
        game_state.discard_card(player, card)


def greed(game_state: "GameState", player: "PlayerState") -> None:
    """Gain a Copper to the top of the player's deck."""

    if game_state.supply.get("Copper", 0) <= 0:
        return

    copper = get_card("Copper")
    game_state.supply["Copper"] -= 1
    game_state.gain_card(player, copper, to_deck=True)


def haunting(game_state: "GameState", player: "PlayerState") -> None:
    """Topdeck a card if the player has at least four in hand."""

    if len(player.hand) < 4:
        return

    choices = list(player.hand)
    selected = player.ai.choose_cards_to_discard(game_state, player, choices, 1)
    card = selected[0] if selected else choices[0]
    if card in player.hand:
        player.hand.remove(card)
        player.deck.append(card)


def locusts(game_state: "GameState", player: "PlayerState") -> None:
    """Trash the top deck card and gain an appropriate replacement."""

    if not player.deck:
        player.shuffle_discard_into_deck()
    if not player.deck:
        return

    trashed = player.deck.pop()
    game_state.trash_card(player, trashed)

    if trashed.name in {"Copper", "Estate"}:
        game_state.give_curse_to_player(player)
        return

    trashed_types = set(trashed.types)
    trashed_cost = trashed.cost.coins
    candidates = []
    for name, count in game_state.supply.items():
        if count <= 0:
            continue
        card = get_card(name)
        if card.cost.coins < trashed_cost and trashed_types.intersection(card.types):
            candidates.append(card)

    if candidates:
        gain = max(candidates, key=lambda c: (c.cost.coins, c.stats.cards, c.name))
        game_state.supply[gain.name] -= 1
        game_state.gain_card(player, gain)


def misery(game_state: "GameState", player: "PlayerState") -> None:
    """Increase the player's Misery penalty."""

    player.misery = min(2, player.misery + 1)


def plague(game_state: "GameState", player: "PlayerState") -> None:
    """Give the player a Curse directly to hand."""

    game_state.give_curse_to_player(player, to_hand=True)


def poverty(game_state: "GameState", player: "PlayerState") -> None:
    """Force the player to discard down to three cards."""

    discard_target = max(0, len(player.hand) - 3)
    if discard_target <= 0:
        return

    choices = list(player.hand)
    selected = player.ai.choose_cards_to_discard(game_state, player, choices, discard_target)
    if len(selected) < discard_target:
        remaining = [card for card in choices if card not in selected]
        selected.extend(remaining[: discard_target - len(selected)])

    for card in selected[:discard_target]:
        if card in player.hand:
            player.hand.remove(card)
            game_state.discard_card(player, card)


def war(game_state: "GameState", player: "PlayerState") -> None:
    """Reveal until a card costing $3 or $4 is trashed."""

    revealed = []
    target = None

    while True:
        if not player.deck:
            player.shuffle_discard_into_deck()
        if not player.deck:
            break
        card = player.deck.pop()
        revealed.append(card)
        if card.cost.coins in (3, 4):
            target = card
            break

    if target:
        revealed.pop()
        game_state.trash_card(player, target)
        for card in revealed:
            game_state.discard_card(player, card)
    else:
        for card in revealed:
            game_state.discard_card(player, card)


HEX_EFFECTS: dict[str, HexEffect] = {
    "Bad Omens": bad_omens,
    "Delusion": delusion,
    "Envy": envy,
    "Famine": famine,
    "Fear": fear,
    "Greed": greed,
    "Haunting": haunting,
    "Locusts": locusts,
    "Misery": misery,
    "Plague": plague,
    "Poverty": poverty,
    "War": war,
}


def create_hex_deck() -> list[str]:
    """Return a shuffled list of Hex names for a new game."""

    names = list(HEX_EFFECTS.keys())
    random.shuffle(names)
    return names


def resolve_hex(name: str, game_state: "GameState", player: "PlayerState") -> None:
    """Execute the Hex ``name`` for ``player`` if it exists."""

    effect = HEX_EFFECTS.get(name)
    if effect is not None:
        effect(game_state, player)

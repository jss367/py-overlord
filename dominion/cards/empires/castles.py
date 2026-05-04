"""Implementation of the Castles split pile from Empires.

The Castles pile contains eight different Victory cards stacked from
cheapest (Humble Castle, on top) to most expensive (King's Castle, on
bottom). Only the topmost Castle still in the pile may be bought or
gained at any time. With 2 players the pile contains one of each
Castle; with 3 or more it contains two of each.
"""

from typing import Optional

from ..base_card import Card, CardCost, CardStats, CardType


CASTLE_PILE_ORDER = (
    "Humble Castle",
    "Crumbling Castle",
    "Small Castle",
    "Haunted Castle",
    "Opulent Castle",
    "Sprawling Castle",
    "Grand Castle",
    "King's Castle",
)


class CastleSplitCard(Card):
    """Common base for the Castles split pile."""

    upper_partners: tuple[str, ...] = ()

    def starting_supply(self, game_state) -> int:
        return 1 if len(game_state.players) <= 2 else 2

    def may_be_bought(self, game_state) -> bool:
        for partner in self.upper_partners:
            if game_state.supply.get(partner, 0) > 0:
                return False
        return super().may_be_bought(game_state)


def _gain_topmost_castle(game_state, player) -> Optional[Card]:
    """Gain whichever Castle is currently on top of the pile."""
    from ..registry import get_card

    for name in CASTLE_PILE_ORDER:
        if game_state.supply.get(name, 0) > 0:
            game_state.supply[name] -= 1
            return game_state.gain_card(player, get_card(name))
    return None


class HumbleCastle(CastleSplitCard):
    """$3 Treasure-Victory: $1; worth 1 VP per Castle you have."""

    upper_partners = ()

    def __init__(self):
        super().__init__(
            name="Humble Castle",
            cost=CardCost(coins=3),
            stats=CardStats(coins=1),
            types=[CardType.TREASURE, CardType.VICTORY],
        )

    def get_victory_points(self, player) -> int:
        return sum(1 for card in player.all_cards() if "Castle" in card.name)


class CrumblingCastle(CastleSplitCard):
    """$4 Victory: 1 VP. When gained or trashed: +1 VP and gain a Silver."""

    upper_partners = ("Humble Castle",)

    def __init__(self):
        super().__init__(
            name="Crumbling Castle",
            cost=CardCost(coins=4),
            stats=CardStats(vp=1),
            types=[CardType.VICTORY],
        )

    def _resolve_bonus(self, game_state, player) -> None:
        from ..registry import get_card

        player.vp_tokens += 1
        if game_state.supply.get("Silver", 0) > 0:
            game_state.supply["Silver"] -= 1
            game_state.gain_card(player, get_card("Silver"))

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)
        self._resolve_bonus(game_state, player)

    def on_trash(self, game_state, player):
        super().on_trash(game_state, player)
        self._resolve_bonus(game_state, player)


class SmallCastle(CastleSplitCard):
    """$5 Action-Victory: 2 VP. Trash this or a Castle from your hand;
    gain a Castle."""

    upper_partners = ("Humble Castle", "Crumbling Castle")

    def __init__(self):
        super().__init__(
            name="Small Castle",
            cost=CardCost(coins=5),
            stats=CardStats(vp=2),
            types=[CardType.ACTION, CardType.VICTORY],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        castles_in_hand = [card for card in player.hand if "Castle" in card.name]
        candidates: list[Card] = list(castles_in_hand)
        if self in player.in_play:
            candidates.append(self)

        if not candidates:
            return

        chosen = player.ai.choose_card_to_trash(game_state, list(candidates))
        if chosen is None or chosen not in candidates:
            chosen = candidates[0]

        if chosen is self and self in player.in_play:
            player.in_play.remove(self)
            game_state.trash_card(player, self)
        elif chosen in player.hand:
            player.hand.remove(chosen)
            game_state.trash_card(player, chosen)
        else:
            return

        _gain_topmost_castle(game_state, player)


class HauntedCastle(CastleSplitCard):
    """$6 Victory: 2 VP. When you gain this on your turn, gain a Gold and
    each other player with 5 or more cards in hand puts 2 onto their deck."""

    upper_partners = ("Humble Castle", "Crumbling Castle", "Small Castle")

    def __init__(self):
        super().__init__(
            name="Haunted Castle",
            cost=CardCost(coins=6),
            stats=CardStats(vp=2),
            types=[CardType.VICTORY],
        )

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)
        if player is not game_state.current_player:
            return

        from ..registry import get_card

        if game_state.supply.get("Gold", 0) > 0:
            game_state.supply["Gold"] -= 1
            game_state.gain_card(player, get_card("Gold"))

        def attack_target(target):
            if len(target.hand) < 5:
                return
            picks = target.ai.choose_cards_to_discard(
                game_state, target, list(target.hand), 2, reason="haunted_castle"
            )
            chosen: list[Card] = []
            for card in picks:
                if card in target.hand and card not in chosen:
                    chosen.append(card)
                if len(chosen) == 2:
                    break
            while len(chosen) < 2 and target.hand:
                fallback = target.hand[-1]
                if fallback in chosen:
                    break
                chosen.append(fallback)
            for card in chosen[:2]:
                if card in target.hand:
                    target.hand.remove(card)
                    target.deck.append(card)

        for other in game_state.players:
            if other is player:
                continue
            game_state.attack_player(other, attack_target)


class OpulentCastle(CastleSplitCard):
    """$7 Action-Victory: 3 VP. Discard any number of Victory cards revealed
    from your hand for +$2 each."""

    upper_partners = (
        "Humble Castle",
        "Crumbling Castle",
        "Small Castle",
        "Haunted Castle",
    )

    def __init__(self):
        super().__init__(
            name="Opulent Castle",
            cost=CardCost(coins=7),
            stats=CardStats(vp=3),
            types=[CardType.ACTION, CardType.VICTORY],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        victory_in_hand = [card for card in player.hand if card.is_victory]
        if not victory_in_hand:
            return

        chooser = getattr(player.ai, "choose_cards_to_discard", None)
        chosen: list[Card] = []
        if chooser is not None:
            picks = chooser(
                game_state,
                player,
                list(victory_in_hand),
                len(victory_in_hand),
                reason="opulent_castle",
            ) or []
            for card in picks:
                if card in victory_in_hand and card not in chosen:
                    chosen.append(card)
        if not chosen:
            chosen = list(victory_in_hand)

        for card in chosen:
            if card in player.hand:
                player.hand.remove(card)
                game_state.discard_card(player, card)
                player.coins += 2


class SprawlingCastle(CastleSplitCard):
    """$8 Victory: 4 VP. When gained, gain a Duchy and 3 Estates."""

    upper_partners = (
        "Humble Castle",
        "Crumbling Castle",
        "Small Castle",
        "Haunted Castle",
        "Opulent Castle",
    )

    def __init__(self):
        super().__init__(
            name="Sprawling Castle",
            cost=CardCost(coins=8),
            stats=CardStats(vp=4),
            types=[CardType.VICTORY],
        )

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)
        from ..registry import get_card

        if game_state.supply.get("Duchy", 0) > 0:
            game_state.supply["Duchy"] -= 1
            game_state.gain_card(player, get_card("Duchy"))
        for _ in range(3):
            if game_state.supply.get("Estate", 0) <= 0:
                break
            game_state.supply["Estate"] -= 1
            game_state.gain_card(player, get_card("Estate"))


class GrandCastle(CastleSplitCard):
    """$9 Victory: 5 VP. When gained, reveal your hand and +1 VP per
    Victory card in hand and in play."""

    upper_partners = (
        "Humble Castle",
        "Crumbling Castle",
        "Small Castle",
        "Haunted Castle",
        "Opulent Castle",
        "Sprawling Castle",
    )

    def __init__(self):
        super().__init__(
            name="Grand Castle",
            cost=CardCost(coins=9),
            stats=CardStats(vp=5),
            types=[CardType.VICTORY],
        )

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)
        bonus = sum(1 for card in player.hand if card.is_victory)
        bonus += sum(1 for card in player.in_play if card.is_victory)
        bonus += sum(1 for card in player.duration if card.is_victory)
        player.vp_tokens += bonus


class KingsCastle(CastleSplitCard):
    """$10 Victory: 2 VP per Castle you have."""

    upper_partners = (
        "Humble Castle",
        "Crumbling Castle",
        "Small Castle",
        "Haunted Castle",
        "Opulent Castle",
        "Sprawling Castle",
        "Grand Castle",
    )

    def __init__(self):
        super().__init__(
            name="King's Castle",
            cost=CardCost(coins=10),
            stats=CardStats(),
            types=[CardType.VICTORY],
        )

    def get_victory_points(self, player) -> int:
        return 2 * sum(1 for card in player.all_cards() if "Castle" in card.name)

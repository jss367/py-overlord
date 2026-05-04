"""The Knights split-pile from Dark Ages.

There are ten unique Knights. The Knights pile is a single supply pile
shuffled at game start; only the top Knight is face up and available to be
bought or gained. Each Knight is an Action-Attack-Knight ($5).

Generic attack: +$2. Each other player reveals the top 2 cards of their deck,
trashes one of them costing $3-$6 (attacker's choice), discards the rest. If
a Knight is trashed by this attack, also trash the attacking Knight.

Per-knight extras are listed in each subclass.
"""

from typing import Optional

from ..base_card import Card, CardCost, CardStats, CardType


class _BaseKnight(Card):
    """Base class wiring up the shared Knight attack."""

    def __init__(self, name: str, stats: CardStats | None = None):
        super().__init__(
            name=name,
            cost=CardCost(coins=5),
            stats=stats or CardStats(),
            types=[CardType.ACTION, CardType.ATTACK, CardType.KNIGHT],
        )

    def starting_supply(self, game_state) -> int:
        return 0  # Knights pile owns the count

    def may_be_bought(self, game_state) -> bool:
        return False  # only the top Knight is buyable

    # --- standard Knight attack ----------------------------------------

    def _resolve_knight_attack(self, game_state):
        from ..registry import get_card  # noqa: F401

        attacker = game_state.current_player
        attacker.coins += 2

        knight_was_trashed = False

        def attack_target(target):
            nonlocal knight_was_trashed
            revealed: list[Card] = []
            for _ in range(2):
                if not target.deck and target.discard:
                    target.shuffle_discard_into_deck()
                if not target.deck:
                    break
                revealed.append(target.deck.pop())

            if not revealed:
                return

            game_state.log_callback(
                (
                    "action",
                    target.ai.name,
                    f"reveals top of deck for {self.name}: {[c.name for c in revealed]}",
                    {"revealed": [c.name for c in revealed]},
                )
            )

            trashable = [
                c for c in revealed if 3 <= c.cost.coins <= 6
            ]

            if trashable:
                if len(trashable) == 1:
                    chosen = trashable[0]
                else:
                    chosen = attacker.ai.choose_knight_to_trash(
                        game_state, attacker, target, list(trashable)
                    )
                    if chosen not in trashable:
                        chosen = max(
                            trashable, key=lambda c: (c.cost.coins, c.name)
                        )
                revealed.remove(chosen)
                if chosen.is_knight:
                    knight_was_trashed = True
                game_state.trash_card(target, chosen)

            for card in revealed:
                game_state.discard_card(target, card)

        for other in game_state.players:
            if other is attacker:
                continue
            game_state.attack_player(other, attack_target)

        # If a Knight was trashed by this attack, also trash this Knight.
        if knight_was_trashed and self in attacker.in_play:
            attacker.in_play.remove(self)
            game_state.trash_card(attacker, self)

    def play_effect(self, game_state):
        self._do_extra(game_state)
        self._resolve_knight_attack(game_state)

    def _do_extra(self, game_state):
        """Hook for per-knight extras that resolve before the attack."""


# ---------- Sirs (extras resolve before / alongside the attack) ----------


class SirBailey(_BaseKnight):
    """+1 Card +1 Action + standard attack."""

    def __init__(self):
        super().__init__("Sir Bailey", CardStats(cards=1, actions=1))


class SirDestry(_BaseKnight):
    """+2 Cards + standard attack."""

    def __init__(self):
        super().__init__("Sir Destry", CardStats(cards=2))


class SirMartin(_BaseKnight):
    """+1 Buy + standard attack."""

    def __init__(self):
        super().__init__("Sir Martin", CardStats(buys=1))


class SirMichael(_BaseKnight):
    """Standard attack + each other player discards down to 3 cards."""

    def __init__(self):
        super().__init__("Sir Michael")

    def _do_extra(self, game_state):
        attacker = game_state.current_player
        for other in game_state.players:
            if other is attacker:
                continue

            def discard_down(target):
                while len(target.hand) > 3:
                    excess = len(target.hand) - 3
                    chosen = target.ai.choose_cards_to_discard(
                        game_state, target, list(target.hand), excess,
                        reason="sir_michael",
                    )
                    if not chosen:
                        # Fall back: discard arbitrary cards
                        chosen = target.hand[:excess]
                    discarded = 0
                    for card in chosen:
                        if card in target.hand and discarded < excess:
                            target.hand.remove(card)
                            game_state.discard_card(target, card)
                            discarded += 1
                    if discarded == 0:
                        break

            game_state.attack_player(other, discard_down)


class SirVander(_BaseKnight):
    """When trashed, gain a Gold."""

    def __init__(self):
        super().__init__("Sir Vander")

    def on_trash(self, game_state, player):
        from ..registry import get_card

        if game_state.supply.get("Gold", 0) > 0:
            game_state.supply["Gold"] -= 1
            game_state.gain_card(player, get_card("Gold"))


# ---------- Dames ----------


class DameAnna(_BaseKnight):
    """You may trash up to 2 cards from your hand. Then standard attack."""

    def __init__(self):
        super().__init__("Dame Anna")

    def _do_extra(self, game_state):
        player = game_state.current_player
        choices = list(player.hand)
        to_trash = player.ai.choose_dame_anna_trash(game_state, player, choices)
        for card in to_trash[:2]:
            if card in player.hand:
                player.hand.remove(card)
                game_state.trash_card(player, card)


class DameJosephine(_BaseKnight):
    """2 VP + standard attack."""

    def __init__(self):
        super().__init__("Dame Josephine")
        # Knights are Action-Attack-Knight; Josephine is also a Victory card.
        self.types = list(self.types) + [CardType.VICTORY]
        self.stats = CardStats(vp=2)


class DameMolly(_BaseKnight):
    """+2 Actions + standard attack."""

    def __init__(self):
        super().__init__("Dame Molly", CardStats(actions=2))


class DameNatalie(_BaseKnight):
    """You may gain a card costing up to $3. Then standard attack."""

    def __init__(self):
        super().__init__("Dame Natalie")

    def _do_extra(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        candidates: list[Card] = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            try:
                c = get_card(name)
            except ValueError:
                continue
            cost = game_state.get_card_cost(player, c)
            if cost <= 3 and c.may_be_bought(game_state):
                candidates.append(c)

        choice = player.ai.choose_card_to_gain_with_dame_natalie(
            game_state, player, candidates
        )
        if choice and game_state.supply.get(choice.name, 0) > 0:
            game_state.supply[choice.name] -= 1
            game_state.gain_card(player, get_card(choice.name))


class DameSylvia(_BaseKnight):
    """+$2 (so $4 total this play) + standard attack.

    Implementation: extra +$2 happens via stats.coins, the attack itself adds
    its $2 inside ``_resolve_knight_attack``.
    """

    def __init__(self):
        super().__init__("Dame Sylvia", CardStats(coins=2))


# ---------- Pile placeholder ----------


class KnightsPile(Card):
    """Placeholder used by the registry for the "Knights" pile name.

    The actual game state has a ``pile_order["Knights"]`` listing the
    individual knight cards (top at end). ``get_card("Knights")`` returns this
    placeholder so cost / display logic has something to work with.
    """

    def __init__(self):
        super().__init__(
            name="Knights",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.ATTACK, CardType.KNIGHT],
        )

    def starting_supply(self, game_state) -> int:
        return 10  # 10 unique Knights

    def may_be_bought(self, game_state) -> bool:
        return False  # the *top* Knight is what's bought, not "Knights"


KNIGHT_CLASSES = (
    SirBailey,
    SirDestry,
    SirMartin,
    SirMichael,
    SirVander,
    DameAnna,
    DameJosephine,
    DameMolly,
    DameNatalie,
    DameSylvia,
)

KNIGHT_NAMES = tuple(cls().name for cls in KNIGHT_CLASSES)

"""Way of the Chameleon — Follow the card's instructions, swapping +Cards
and +$ (each ``+Cards`` becomes ``+$`` and vice versa).

Important: the swap applies ONLY to instructions on the chosen card itself
that are written as "+Cards" or "+$". It does NOT apply to:

- Imperative draws like "draw until you have 6 cards in hand" (Cursed
  Village) or "set aside the top card; draw it" (Library) — these are
  not "+Cards" instructions.
- Imperative coin gains that aren't "+$" wording.
- Cards played as a side effect of the chosen card (e.g. Vassal -> Action,
  Throne Room -> Action, Fortune Hunter -> Treasure). Those run their own
  normal effects, even if the side-effect card overrides ``on_play`` and
  uses the chameleon helpers.

To support cards whose "+Cards"/"+$" appears in ``play_effect`` (because
the value depends on a choice or condition), play_effect bodies use the
helpers ``chameleon_plus_cards`` / ``chameleon_plus_coins`` exposed below.
The helpers route the value into the swap accumulator only when the
currently-resolving card is the chameleon-targeted card itself; when a
nested side-effect play is in progress, the helpers fall back to
``draw_cards`` / ``player.coins +=`` exactly as before.
"""

from contextlib import contextmanager

from .base_way import Way


# Module-level state for the active chameleon swap. Only one swap is
# active at a time (the outer-card resolution); nested plays don't swap.
_active_state: dict | None = None


def _chameleon_is_active(player) -> bool:
    """Return True when a Chameleon swap is in progress for ``player`` AND
    the currently-resolving card is the chameleon-targeted card itself.

    Side-effect plays (Vassal->Village, Throne Room->Smithy, Fortune
    Hunter->Bauble, etc.) push a nested entry onto the resolution stack,
    so they do not see the swap even if the nested card uses the helpers
    via an overridden ``on_play``.
    """
    s = _active_state
    if not s or s["player"] is not player:
        return False
    stack = s["stack"]
    target = s["target_card"]
    # Only swap when the chameleon-targeted card is currently on top of
    # the resolution stack (i.e. we are inside its body, not inside a
    # nested side-effect play).
    return bool(stack) and stack[-1] is target


def chameleon_plus_cards(game_state, player, count: int) -> None:
    """Imperative ``+Cards`` instruction in a card's ``play_effect``.

    Use this in play_effect bodies for "+Cards" wording (the value is
    written on the card as ``+Cards``). Do NOT use it for imperative
    draws like "draw until you have 6 in hand" or "draw the set-aside
    card" — those are not ``+Cards`` instructions and must not swap.

    When a Chameleon swap is active on this player, the count is
    captured for later conversion to ``+$``. Otherwise the cards are
    drawn normally.
    """
    if count <= 0:
        return
    if _chameleon_is_active(player):
        _active_state["cards_requested"] += count  # type: ignore[index]
        return
    game_state.draw_cards(player, count)


def chameleon_plus_coins(player, amount: int) -> None:
    """Imperative ``+$`` instruction in a card's ``play_effect``.

    Use this in play_effect bodies for "+$" wording (the amount is
    written on the card as ``+$``). Do NOT use it for non-``+$`` coin
    gains.

    When a Chameleon swap is active on this player, the amount is
    captured for later conversion to ``+Cards``. Otherwise the coins
    are added normally.
    """
    if amount <= 0:
        return
    if _chameleon_is_active(player):
        _active_state["coins_requested"] += amount  # type: ignore[index]
        return
    player.coins += amount


@contextmanager
def chameleon_swap_block(game_state, player):
    """Optional context manager wrapping a block of ``+Cards``/``+$``
    instructions inside a play_effect. Inside the block,
    ``game_state.draw_cards`` and ``player.coins +=`` style operations
    are still NOT auto-swapped — callers must use ``chameleon_plus_cards``
    / ``chameleon_plus_coins`` to express +Cards/+$ explicitly. The
    context manager exists for clarity; it is a no-op today and reserved
    for future use.
    """
    yield


class WayOfTheChameleon(Way):
    def __init__(self):
        super().__init__("Way of the Chameleon")

    def apply(self, game_state, card) -> None:
        global _active_state

        player = game_state.current_player

        # Strategy: maintain a resolution stack of card instances. The
        # helpers (``chameleon_plus_cards`` / ``chameleon_plus_coins``)
        # consult ``_chameleon_is_active`` which compares the stack top
        # against the chameleon-targeted card. Side-effect plays (e.g.
        # Vassal->Action, Throne Room->Smithy, Fortune Hunter->Bauble)
        # push a nested entry onto the stack, so even if the nested card
        # has its own ``on_play`` override that calls a helper, the
        # helper sees a non-target stack top and does not swap.
        #
        # To capture every ``on_play`` call — including subclass
        # overrides that bypass ``Card.on_play`` entirely — we patch
        # both ``Card.on_play`` and any subclass that defines its own
        # ``on_play``. Each patched method updates the stack on enter
        # and exit.
        from dominion.cards.base_card import Card

        def _all_subclasses(cls):
            seen = set()
            stack = [cls]
            while stack:
                c = stack.pop()
                for s in c.__subclasses__():
                    if s in seen:
                        continue
                    seen.add(s)
                    yield s
                    stack.append(s)

        prev_state = _active_state
        state: dict = {
            "player": player,
            "target_card": card,
            "stack": [],
            "cards_requested": 0,
            "coins_requested": 0,
        }

        def make_wrapper(original):
            def wrapped(self_card, gs):
                stack = state["stack"]
                stack.append(self_card)
                try:
                    if self_card is card and len(stack) == 1:
                        # The chameleon-targeted card is resolving at
                        # the outer level. Capture its stat-block
                        # ``+Cards`` and ``+$`` for the swap, then zero
                        # them so the card's real ``on_play`` runs
                        # every other effect without re-applying them.
                        if self_card.stats.cards > 0:
                            state["cards_requested"] += self_card.stats.cards
                        if self_card.stats.coins > 0:
                            state["coins_requested"] += self_card.stats.coins

                        saved_cards = self_card.stats.cards
                        saved_coins = self_card.stats.coins
                        self_card.stats.cards = 0
                        self_card.stats.coins = 0
                        try:
                            original(self_card, gs)
                        finally:
                            self_card.stats.cards = saved_cards
                            self_card.stats.coins = saved_coins
                    else:
                        # Nested side-effect play, OR the targeted card
                        # being re-entered from inside its own body
                        # (rare). Either way, run the original on_play
                        # unchanged; the helpers will see a non-target
                        # stack top and refuse to swap.
                        original(self_card, gs)
                finally:
                    stack.pop()
            return wrapped

        # Patch Card.on_play and every subclass that has its own
        # on_play override. Save originals so we can restore them.
        patched: list[tuple[type, str, object]] = []

        def patch(cls):
            original = cls.__dict__["on_play"]
            patched.append((cls, "on_play", original))
            cls.on_play = make_wrapper(original)  # type: ignore[assignment]

        patch(Card)
        for sub in _all_subclasses(Card):
            if "on_play" in sub.__dict__:
                patch(sub)

        _active_state = state
        card._chameleon_active = True
        try:
            # Invoke through the patched ``on_play`` resolution so the
            # most-derived override (Bauble.on_play, Contract.on_play,
            # ...) runs and the stack is updated correctly.
            type(card).on_play(card, game_state)
        finally:
            for cls, attr, original in patched:
                setattr(cls, attr, original)
            _active_state = prev_state
            card._chameleon_active = False

        cards_requested = state["cards_requested"]
        coins_requested = state["coins_requested"]

        # Apply the swap: captured +Cards become +$, captured +$ become
        # the same number of drawn cards.
        if coins_requested > 0:
            game_state.draw_cards(player, coins_requested)
        if cards_requested > 0:
            player.coins += cards_requested

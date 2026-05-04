"""Tournament Prize cards (Cornucopia 1E non-supply pile).

These five cards form the Prize pile that is used by the Tournament Kingdom
card. Prizes are non-supply: they cannot be bought, only gained by Tournament.
There is exactly one of each Prize per game.
"""

from ..base_card import Card, CardCost, CardStats, CardType


PRIZE_CARD_NAMES = [
    "Bag of Gold",
    "Diadem",
    "Followers",
    "Princess",
    "Trusty Steed",
]


class _PrizeCard(Card):
    """Mixin-ish base: Prizes are always non-supply, one copy per game."""

    def may_be_bought(self, game_state) -> bool:  # pragma: no cover - trivial
        return False

    def starting_supply(self, game_state) -> int:  # pragma: no cover - trivial
        return 1


class BagOfGold(_PrizeCard):
    """Prize ($0 Action): +1 Action. Gain a Gold, putting it on top of your deck."""

    def __init__(self):
        super().__init__(
            name="Bag of Gold",
            cost=CardCost(coins=0),
            stats=CardStats(actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        if game_state.supply.get("Gold", 0) <= 0:
            return
        game_state.supply["Gold"] -= 1
        game_state.gain_card(player, get_card("Gold"), to_deck=True)


class Diadem(_PrizeCard):
    """Prize ($0 Treasure): worth $2. When played, +$1 per unused Action."""

    def __init__(self):
        super().__init__(
            name="Diadem",
            cost=CardCost(coins=0),
            stats=CardStats(coins=2),
            types=[CardType.TREASURE],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        # Diadem grants +$1 per *unused* Action at the time it is played.
        # ``player.actions`` already represents currently-unused Actions.
        unused_actions = max(0, player.actions)
        player.coins += unused_actions


class Followers(_PrizeCard):
    """Prize ($0 Action-Attack): +2 Cards, gain Estate, opponents +Curse, discard to 3."""

    def __init__(self):
        super().__init__(
            name="Followers",
            cost=CardCost(coins=0),
            stats=CardStats(cards=2),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player

        # Gain an Estate (from supply) — but if the Estate pile is empty, no
        # Estate is gained. The rest of the effect still resolves.
        if game_state.supply.get("Estate", 0) > 0:
            game_state.supply["Estate"] -= 1
            game_state.gain_card(player, get_card("Estate"))

        def attack_target(target):
            # Curse first.
            game_state.give_curse_to_player(target)
            # Then discard down to 3 cards in hand.
            excess = len(target.hand) - 3
            if excess > 0:
                choices = target.ai.choose_cards_to_discard(
                    game_state, target, list(target.hand), excess, reason="followers"
                )
                chosen: list[Card] = []
                for card in choices:
                    if card in target.hand and len(chosen) < excess:
                        chosen.append(card)
                if len(chosen) < excess:
                    remaining = [c for c in target.hand if c not in chosen]
                    remaining.sort(key=lambda c: (c.cost.coins, c.name))
                    chosen.extend(remaining[: excess - len(chosen)])
                for card in chosen:
                    if card in target.hand:
                        target.hand.remove(card)
                        game_state.discard_card(target, card)

        for other in game_state.players:
            if other is player:
                continue
            game_state.attack_player(other, attack_target, attack_card=self)


class Princess(_PrizeCard):
    """Prize ($0 Action): +1 Buy. While in play, cards cost $2 less (min $0)."""

    def __init__(self):
        super().__init__(
            name="Princess",
            cost=CardCost(coins=0),
            stats=CardStats(buys=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        # Cost reduction "while in play" — we use the per-turn cost_reduction
        # bucket the engine already supports (Highway, Bridge). Princess goes
        # to cleanup at end of turn, so this matches "while in play" closely
        # enough for our simulator.
        player = game_state.current_player
        player.cost_reduction += 2


class TrustySteed(_PrizeCard):
    """Prize ($0 Action): Choose two: +2 Cards / +2 Actions / +$2 / gain 4 Silvers."""

    def __init__(self):
        super().__init__(
            name="Trusty Steed",
            cost=CardCost(coins=0),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player

        options = ["cards", "actions", "coins", "silvers"]
        ai = player.ai
        chosen: list[str]
        if hasattr(ai, "choose_trusty_steed_options"):
            picked = ai.choose_trusty_steed_options(game_state, player, list(options))
            # Sanitize: must be two distinct valid options.
            seen: list[str] = []
            for opt in picked or []:
                if opt in options and opt not in seen:
                    seen.append(opt)
                if len(seen) == 2:
                    break
            if len(seen) < 2:
                # Fill with sensible defaults.
                for opt in ("cards", "actions", "coins", "silvers"):
                    if opt not in seen:
                        seen.append(opt)
                    if len(seen) == 2:
                        break
            chosen = seen
        else:
            # Default: +2 Cards and +2 Actions (a generic "Lab + Village").
            chosen = ["cards", "actions"]

        for opt in chosen:
            if opt == "cards":
                game_state.draw_cards(player, 2)
            elif opt == "actions":
                player.actions += 2
            elif opt == "coins":
                player.coins += 2
            elif opt == "silvers":
                # Gain 4 Silvers, then put your deck into your discard pile.
                for _ in range(4):
                    if game_state.supply.get("Silver", 0) <= 0:
                        break
                    game_state.supply["Silver"] -= 1
                    game_state.gain_card(player, get_card("Silver"))
                # Move remaining deck to discard
                if player.deck:
                    player.discard.extend(player.deck)
                    player.deck = []

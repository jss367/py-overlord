"""Quartermaster from the Plunder expansion."""

from ..base_card import Card, CardCost, CardStats, CardType


class Quartermaster(Card):
    """$5 Action-Duration: At the start of each of your turns (including this
    one), choose one: gain a card costing up to $4 onto this; or take a card
    from this onto your hand.
    """

    def __init__(self):
        super().__init__(
            name="Quartermaster",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.DURATION],
        )
        self.duration_persistent = True
        self.set_aside: list = []

    def play_effect(self, game_state):
        player = game_state.current_player
        self._do_choice(game_state, player)
        if self not in player.duration:
            player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        self._do_choice(game_state, player)
        # Stays in play forever — Quartermaster never discards itself.
        self.duration_persistent = True

    def _do_choice(self, game_state, player):
        from ..registry import get_card

        decision = "gain"
        if hasattr(player.ai, "quartermaster_choice"):
            decision = player.ai.quartermaster_choice(
                game_state, player, list(self.set_aside)
            )
            if decision not in {"gain", "take"}:
                decision = "gain"

        if decision == "take" and self.set_aside:
            chosen = player.ai.choose_action(
                game_state, list(self.set_aside) + [None]
            )
            if chosen is None or chosen not in self.set_aside:
                chosen = self.set_aside[0]
            self.set_aside.remove(chosen)
            player.hand.append(chosen)
            return

        candidates = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            card = get_card(name)
            if card.cost.coins <= 4 and card.cost.potions == 0:
                candidates.append(card)

        if not candidates:
            return

        choice = player.ai.choose_buy(game_state, list(candidates) + [None])
        if choice is None or game_state.supply.get(choice.name, 0) <= 0:
            candidates.sort(key=lambda c: (c.cost.coins, c.name), reverse=True)
            choice = candidates[0]

        game_state.supply[choice.name] -= 1
        gained = game_state.gain_card(player, choice)

        # Pull the gained card out of the discard/deck/hand and onto the mat.
        # If a gain reaction (Watchtower, Trader, etc.) already moved or
        # replaced the card, leave it alone — adding it to set_aside would
        # cause the same instance to live in two zones.
        if gained in player.discard:
            player.discard.remove(gained)
            self.set_aside.append(gained)
        elif gained in player.deck:
            player.deck.remove(gained)
            self.set_aside.append(gained)
        elif gained in player.hand:
            player.hand.remove(gained)
            self.set_aside.append(gained)
        # Otherwise: card was redirected (e.g., Watchtower trashed it,
        # Trader exchanged it for Silver). Don't track it on the mat.

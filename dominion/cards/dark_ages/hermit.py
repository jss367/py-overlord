"""Hermit — $3 Action that trashes junk and may turn into a Madman."""

from ..base_card import Card, CardCost, CardStats, CardType


class Hermit(Card):
    """Look through your discard, you may trash a non-Treasure from discard or
    hand, then gain a card costing up to $3.

    At the end of your Buy phase this turn, if you didn't gain any cards in it,
    trash this Hermit and gain a Madman.
    """

    def __init__(self):
        super().__init__(
            name="Hermit",
            cost=CardCost(coins=3),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def get_additional_non_supply_piles(self) -> dict[str, int]:
        return {"Madman": 10}

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player

        # 1. May trash a non-Treasure from discard or hand.
        choices = [c for c in player.discard + player.hand if not c.is_treasure]
        chosen = player.ai.should_trash_with_hermit(game_state, player, choices)
        if chosen and chosen in choices:
            if chosen in player.hand:
                player.hand.remove(chosen)
            elif chosen in player.discard:
                player.discard.remove(chosen)
            game_state.trash_card(player, chosen)

        # 2. Gain a card costing up to $3.
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

        gain_choice = player.ai.choose_card_to_gain_with_hermit(
            game_state, player, candidates
        )
        if gain_choice and game_state.supply.get(gain_choice.name, 0) > 0:
            game_state.supply[gain_choice.name] -= 1
            game_state.gain_card(player, get_card(gain_choice.name))

        # 3. Track Hermit for end-of-buy-phase Madman conversion.
        # We watch the player's cards-gained-this-buy-phase counter at end of
        # buy phase; this hook hangs off the Hermit instance via on_buy_phase_end.
        # Hermit's reactive trigger lives on the card while it's in play.

    def on_buy_phase_end(self, game_state):
        """At end of buy phase: if no cards were gained, exchange self for a Madman.

        Current card text (2022 errata) says *exchange*, not trash: the Hermit
        goes back onto its Supply pile and a Madman comes out of the Madman
        pile. It never touches the trash, so Shaman-style "gain from the
        trash" effects cannot recover it. If the Madman pile is empty the
        exchange fails and the Hermit stays in play.
        """
        from ..registry import get_card

        player = game_state.current_player
        # Only fire if this Hermit is still in play (didn't get trashed already)
        if self not in player.in_play:
            return
        if getattr(player, "cards_gained_this_buy_phase", 0) > 0:
            return
        if game_state.supply.get("Madman", 0) <= 0:
            return

        # Return this Hermit to its Supply pile.
        player.in_play.remove(self)
        if not game_state._restore_to_supply_pile(self):
            # No pile to return to (should not happen for a Supply Hermit);
            # put it back in play rather than letting the card vanish.
            player.in_play.append(self)
            return
        game_state.log_callback(
            ("action", player.ai.name, "exchanges Hermit for a Madman", {})
        )

        # Take a Madman from the Madman pile (non-supply pile). Exchanging is
        # not gaining: no gain reactions (Sheepdog, Trader, Watchtower), no
        # gain counters, no on-gain hooks. The card goes straight to discard.
        game_state.supply["Madman"] -= 1
        player.discard.append(get_card("Madman"))

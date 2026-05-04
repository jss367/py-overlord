"""Tournament (Cornucopia 1E)."""

from ..base_card import Card, CardCost, CardStats, CardType
from .prizes import PRIZE_CARD_NAMES


class Tournament(Card):
    """Tournament — $4 Action.

    +1 Action. Each player may reveal a Province from his hand. If you do,
    discard it and gain a Prize (from the Prize pile) or a Duchy, putting
    it on top of your deck. If no-one (including you) reveals a Province,
    +1 Card and +$1.
    """

    def __init__(self):
        super().__init__(
            name="Tournament",
            cost=CardCost(coins=4),
            stats=CardStats(actions=1),
            types=[CardType.ACTION],
        )

    def get_additional_piles(self) -> dict[str, int]:
        # Each Prize is a single non-supply card forming the Prize pile.
        return {name: 1 for name in PRIZE_CARD_NAMES}

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player

        # Active player may reveal a Province from their hand. AI hook gates
        # the reveal — by default we always reveal because the trade is
        # strictly favorable in our simulator (Province → Prize or Duchy on
        # top of deck, and Province is set aside but stays in play
        # consistent with original card text — we discard it).
        active_revealed = False
        active_province: Card | None = None
        for card in player.hand:
            if card.name == "Province":
                active_province = card
                break
        if active_province is not None and player.ai.should_reveal_tournament_province(
            game_state, player
        ):
            active_revealed = True

        # Each opponent may also reveal a Province. They do not gain a Prize
        # (only the active player does), but a reveal blocks the +1 Card +$1
        # consolation. We give opponent AIs the same hook so they can choose
        # to reveal (default True — revealing denies the active player the
        # consolation bonus).
        any_other_revealed = False
        for other in game_state.players:
            if other is player:
                continue
            has_province = any(c.name == "Province" for c in other.hand)
            if not has_province:
                continue
            if other.ai.should_reveal_tournament_province(game_state, other):
                any_other_revealed = True
                game_state.log_callback(
                    (
                        "action",
                        other.ai.name,
                        "reveals a Province (Tournament)",
                        {},
                    )
                )

        if active_revealed and active_province is not None:
            # Discard the revealed Province.
            player.hand.remove(active_province)
            game_state.discard_card(player, active_province)
            game_state.log_callback(
                (
                    "action",
                    player.ai.name,
                    "reveals and discards a Province for Tournament",
                    {},
                )
            )

            # Gain a Prize from the Prize pile, or a Duchy. Topdeck whichever
            # is chosen. The AI hook decides which option to take.
            available: list[Card] = []
            for name in PRIZE_CARD_NAMES:
                if game_state.supply.get(name, 0) > 0:
                    available.append(get_card(name))
            if game_state.supply.get("Duchy", 0) > 0:
                available.append(get_card("Duchy"))

            if available:
                choice = player.ai.choose_tournament_prize(
                    game_state, player, available
                )
                if choice is None or choice.name not in {c.name for c in available}:
                    # Default: prefer a Prize over a Duchy.
                    prize_options = [c for c in available if c.name != "Duchy"]
                    choice = prize_options[0] if prize_options else available[0]

                if game_state.supply.get(choice.name, 0) > 0:
                    game_state.supply[choice.name] -= 1
                    game_state.gain_card(player, choice, to_deck=True)
            return

        # No-one revealed a Province → consolation +1 Card +$1.
        if not active_revealed and not any_other_revealed:
            game_state.draw_cards(player, 1)
            player.coins += 1

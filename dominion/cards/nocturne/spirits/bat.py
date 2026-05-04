"""Bat — non-supply Night, $2."""

from ...base_card import Card, CardCost, CardStats, CardType


class Bat(Card):
    """You may trash up to 2 cards from hand. If you do, exchange this for a Vampire."""

    def __init__(self):
        super().__init__(
            name="Bat",
            cost=CardCost(coins=2),
            stats=CardStats(),
            types=[CardType.NIGHT],
        )

    def starting_supply(self, game_state) -> int:
        return 10

    def may_be_bought(self, game_state) -> bool:
        return False

    def play_effect(self, game_state):
        player = game_state.current_player
        choices = list(player.hand)
        # Trash up to 2 junky cards
        to_trash = player.ai.choose_cards_to_trash(game_state, choices, min(2, len(choices)))
        if not to_trash:
            return
        for card in to_trash[:2]:
            if card in player.hand:
                player.hand.remove(card)
                game_state.trash_card(player, card)
        # Exchange Bat for a Vampire from the Vampire pile.
        if game_state.supply.get("Vampire", 0) <= 0:
            return
        if self in player.in_play:
            player.in_play.remove(self)
        # Return the Bat to its pile.
        game_state.supply["Bat"] = game_state.supply.get("Bat", 0) + 1
        game_state.supply["Vampire"] -= 1
        from ...registry import get_card

        game_state.gain_card(player, get_card("Vampire"))

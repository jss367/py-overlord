from ..base_card import Card, CardCost, CardStats, CardType


class WildHunt(Card):
    def __init__(self):
        super().__init__(
            name="Wild Hunt",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        options = ["draw", "estate"]
        choice = player.ai.choose_wild_hunt_option(game_state, player, options)
        if choice not in options:
            choice = "draw"

        if choice == "draw":
            game_state.draw_cards(player, 3)
            game_state.wild_hunt_pile_tokens += 1
            return

        gained = None
        if game_state.supply.get("Estate", 0) > 0:
            game_state.supply["Estate"] -= 1
            gained = game_state.gain_card(player, get_card("Estate"))
        elif any(card.name == "Estate" for card in player.exile):
            gained = game_state.gain_card(player, get_card("Estate"))

        if not gained:
            return

        if gained and gained.name == "Estate":
            player.vp_tokens += game_state.wild_hunt_pile_tokens
            game_state.wild_hunt_pile_tokens = 0

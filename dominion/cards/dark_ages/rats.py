from ..base_card import Card, CardCost, CardStats, CardType


class Rats(Card):
    def __init__(self):
        super().__init__(
            name="Rats",
            cost=CardCost(coins=4),
            stats=CardStats(actions=1, cards=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        # Gain another Rats if available
        if game_state.supply.get("Rats", 0) > 0:
            game_state.supply["Rats"] -= 1
            from ..registry import get_card

            previous = getattr(game_state, "_allow_ferryman_pile_gain", False)
            if game_state._is_ferryman_reserved_pile_name("Rats"):
                game_state._allow_ferryman_pile_gain = True
            try:
                game_state.gain_card(player, get_card("Rats"))
            finally:
                game_state._allow_ferryman_pile_gain = previous
        # Trash a non-Rats card from hand if possible
        choices = [c for c in player.hand if c.name != "Rats"]
        if choices:
            trash_choice = player.ai.choose_card_to_trash(game_state, choices)
            if trash_choice:
                player.hand.remove(trash_choice)
                game_state.trash_card(player, trash_choice)

    def on_trash(self, game_state, player):
        player.draw_cards(1)

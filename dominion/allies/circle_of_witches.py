from .base_ally import Ally
from ..cards.allies._rules import decide


class CircleOfWitches(Ally):
    def __init__(self):
        super().__init__("Circle of Witches")

    def on_play_card(self, game_state, player, card):
        if not card.is_liaison or player.favors < 3:
            return
        if not decide(
            game_state,
            player,
            "circle_of_witches",
            [False, True],
            game_state.supply.get("Curse", 0) > 0,
        ):
            return
        player.favors -= 3
        for opponent in game_state.opponents_in_order(player):
            game_state.give_curse_to_player(opponent)

from dominion.cards.base_card import CardCost
from .base_project import Project


class Innovation(Project):
    """Project that plays the first gained Action each turn."""

    def __init__(self):
        super().__init__("Innovation", CardCost(coins=6))

    def on_gain(self, game_state, player, card, *, claimed=False):
        if not game_state.is_action(card) or (player.innovation_used and not claimed):
            return

        player.innovation_used = True

        if not game_state._remove_gained_card_from_zones(player, card):
            return

        player.in_play.append(card)
        card.on_play(game_state)
        game_state.fire_ally_play_hooks(player, card)

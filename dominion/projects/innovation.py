from dominion.cards.base_card import CardCost
from .base_project import Project


class Innovation(Project):
    """Project that plays the first gained Action each turn."""

    def __init__(self):
        super().__init__("Innovation", CardCost(coins=6))

    def on_gain(self, game_state, player, card):
        if not card.is_action or player.innovation_used:
            return

        player.innovation_used = True

        # Remove the card from wherever it was gained
        if card in player.discard:
            player.discard.remove(card)
        elif card in player.deck:
            player.deck.remove(card)
        elif card in player.hand:
            player.hand.remove(card)

        player.in_play.append(card)
        card.on_play(game_state)

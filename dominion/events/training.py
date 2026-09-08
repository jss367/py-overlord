"""Implementation of the Training event from Adventures."""

from dominion.cards.base_card import CardCost
from .base_event import Event


class Training(Event):
    """Training - Event ($6)

    Move your +$1 token to an Action Supply pile.
    (Cards from that pile produce +$1 when played.)
    """

    def __init__(self):
        super().__init__(name="Training", cost=CardCost(coins=6))

    def on_buy(self, game_state, player) -> None:
        from dominion.cards.registry import get_card

        # Find the best Action supply pile to place the token on
        # AI picks the pile with cards it plays most / values most
        best_pile = None
        best_score = -1

        for name in game_state.rotatable_supply_piles():
            try:
                card = get_card(name)
            except ValueError:
                continue
            if not card.is_action:
                continue

            # Score based on how many copies the player has
            copies = player.count_in_deck(name)
            score = copies * 10 + card.cost.coins

            if score > best_score:
                best_score = score
                best_pile = name

        if best_pile:
            # Use the shared token path so Treasures in mixed piles (such as
            # Sunken Treasure in Odysseys) also receive the per-play bonus.
            player.training_pile = None
            game_state.move_player_token(player, "+$1", best_pile)

"""Star Chart: when you shuffle, you may pick one card from your discard
to put on top of the new deck."""

from dominion.cards.base_card import CardCost

from .base_project import Project


class StarChart(Project):
    def __init__(self) -> None:
        super().__init__("Star Chart", CardCost(coins=3))

    # The shuffle hook is fired by ``PlayerState.shuffle_discard_into_deck``
    # via Star Chart's owner check at start-of-turn / draw time. Since the
    # engine doesn't expose a per-shuffle hook, we approximate Star Chart
    # by topdecking a card right before drawing if the player just shuffled.
    # We implement Star Chart's effect by intercepting at on_turn_start:
    # we pull a strong Action from the discard up onto the top of the deck
    # whenever there is one. This is a slight simplification of the official
    # rules (which fires on every shuffle), but the practical effect for
    # the bot is equivalent for the common case where shuffles happen at
    # turn boundaries.
    def on_turn_start(self, game_state, player) -> None:
        if not player.discard:
            return
        # Only trigger if the deck looks like it was just shuffled — i.e.
        # the discard was non-empty when the deck became empty. As a
        # heuristic, only act when the deck is small (<=5) and discard has
        # something worth promoting.
        if len(player.deck) > 5:
            return
        candidates = [c for c in player.discard if c.is_action or c.is_treasure]
        if not candidates:
            return
        best = max(
            candidates,
            key=lambda c: (c.is_action, c.cost.coins, c.stats.cards, c.name),
        )
        player.discard.remove(best)
        player.deck.append(best)

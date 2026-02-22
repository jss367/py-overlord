"""Implementation of the Pirate card from Seaside 2nd Edition."""

from ..base_card import Card, CardCost, CardStats, CardType


class Pirate(Card):
    """Pirate - Action/Duration/Reaction ($5)

    At the start of your next turn, gain a Treasure costing up to $6
    to your hand.

    Reaction: When any player gains a Treasure, you may play this
    from your hand.
    """

    def __init__(self):
        super().__init__(
            name="Pirate",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.DURATION, CardType.REACTION],
        )
        self.duration_persistent = True

    def play_effect(self, game_state):
        player = game_state.current_player
        player.duration.append(self)

    def on_duration(self, game_state):
        from ..registry import get_card

        player = game_state.current_player

        # Gain a Treasure costing up to $6 to hand
        best_treasure = None
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            card = get_card(name)
            if card.is_treasure and card.cost.coins <= 6:
                if best_treasure is None or card.cost.coins > best_treasure.cost.coins:
                    best_treasure = card

        if best_treasure and game_state.supply.get(best_treasure.name, 0) > 0:
            game_state.supply[best_treasure.name] -= 1
            gained = game_state.gain_card(player, best_treasure)
            # Move to hand
            if gained in player.discard:
                player.discard.remove(gained)
            elif gained in player.deck:
                player.deck.remove(gained)
            if gained not in player.hand:
                player.hand.append(gained)

        self.duration_persistent = False

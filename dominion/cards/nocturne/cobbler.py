"""Cobbler — $5 Action-Night-Duration.

At the start of your next turn, gain a card costing up to $4 to your hand.
"""

from ..base_card import Card, CardCost, CardStats, CardType


class Cobbler(Card):
    def __init__(self):
        super().__init__(
            name="Cobbler",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.NIGHT, CardType.DURATION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        # Add to duration so on_duration fires at start of next turn.
        if self in player.in_play:
            player.in_play.remove(self)
        if self not in player.duration:
            player.duration.append(self)
        self.duration_persistent = True

    def on_duration(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        options = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            try:
                card = get_card(name)
            except ValueError:
                continue
            if card.cost.coins > 4 or card.cost.potions > 0 or card.cost.debt > 0:
                continue
            if not card.may_be_bought(game_state):
                continue
            options.append(card)
        if not options:
            self.duration_persistent = False
            return

        choice = player.ai.choose_card_to_gain_to_hand(game_state, player, options, 4)
        if choice is None:
            choice = max(options, key=lambda c: (c.cost.coins, c.stats.cards, c.name))

        if game_state.supply.get(choice.name, 0) > 0:
            game_state.supply[choice.name] -= 1
            gained = game_state.gain_card(player, choice)
            if gained:
                if gained in player.discard:
                    player.discard.remove(gained)
                elif gained in player.deck:
                    player.deck.remove(gained)
                if gained not in player.hand:
                    player.hand.append(gained)

        self.duration_persistent = False

"""Research: Action-Duration ($4). +1 Action.

Trash a card from your hand. Per $1 it cost, set aside a card from your
deck face down on this. (At the start of your next turn, put them into
your hand.)
"""

from ..base_card import Card, CardCost, CardStats, CardType


class Research(Card):
    def __init__(self) -> None:
        super().__init__(
            name="Research",
            cost=CardCost(coins=4),
            stats=CardStats(actions=1),
            types=[CardType.ACTION, CardType.DURATION],
        )
        self.set_aside: list = []
        self.duration_persistent = False

    def play_effect(self, game_state):
        player = game_state.current_player

        if not player.hand:
            return
        choice = player.ai.choose_card_to_trash(game_state, list(player.hand))
        if choice is None:
            choice = min(
                player.hand,
                key=lambda c: (
                    0 if c.name == "Curse" else (1 if c.name == "Copper" else 2),
                    c.cost.coins,
                    c.name,
                ),
            )
        if choice not in player.hand:
            return

        cost = choice.cost.coins
        player.hand.remove(choice)
        game_state.trash_card(player, choice)

        for _ in range(cost):
            if not player.deck and player.discard:
                player.shuffle_discard_into_deck()
            if not player.deck:
                break
            self.set_aside.append(player.deck.pop())

        # Stay in play until next turn so on_duration fires even if cost was 0.
        player.duration.append(self)
        self.duration_persistent = True

    def on_duration(self, game_state):
        player = game_state.current_player
        if self.set_aside:
            player.hand.extend(self.set_aside)
            self.set_aside = []
        self.duration_persistent = False

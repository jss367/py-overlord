from ..base_card import Card, CardCost, CardStats, CardType


class Prince(Card):
    def __init__(self):
        super().__init__(
            name="Prince",
            cost=CardCost(coins=8),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.DURATION],
        )
        self.duration_persistent = True
        self.set_aside = None

    def play_effect(self, game_state):
        player = game_state.current_player
        choices = [
            card
            for card in player.hand
            if card.is_action and card.cost.coins <= 4
        ]
        if not choices:
            return

        choice = player.ai.choose_card_for_prince(game_state, player, choices + [None])
        if choice is None or choice not in choices:
            choice = max(choices, key=lambda card: (card.cost.coins, card.stats.cards, card.stats.actions, card.name))
        if choice not in player.hand:
            return

        player.hand.remove(choice)
        self.set_aside = choice
        if self not in player.duration:
            player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        if not self.set_aside:
            self.duration_persistent = False
            return

        card = self.set_aside
        player.in_play.append(card)
        card.on_play(game_state)
        if card in player.in_play:
            player.in_play.remove(card)
        if card in player.discard:
            player.discard.remove(card)
        if card in player.deck:
            player.deck.remove(card)
        self.duration_persistent = True

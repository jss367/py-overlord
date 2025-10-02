from ..base_card import Card, CardCost, CardStats, CardType


class Church(Card):
    def __init__(self):
        super().__init__(
            name="Church",
            cost=CardCost(coins=3),
            stats=CardStats(actions=1, buys=1),
            types=[CardType.ACTION, CardType.DURATION],
        )
        self.set_aside: list = []

    def play_effect(self, game_state):
        player = game_state.current_player
        self.set_aside = []
        choices = list(player.hand)
        selected = []
        if choices:
            chosen = player.ai.choose_cards_to_set_aside_with_church(game_state, player, choices)
            selected = [card for card in chosen if card in player.hand]
            for card in selected:
                player.hand.remove(card)
        self.set_aside = selected
        if self not in player.duration:
            player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        if self.set_aside:
            player.hand.extend(self.set_aside)
            self.set_aside = []
        choice = player.ai.choose_card_to_trash_with_church(game_state, player, list(player.hand))
        if choice and choice in player.hand:
            player.hand.remove(choice)
            game_state.trash_card(player, choice)
        self.duration_persistent = False

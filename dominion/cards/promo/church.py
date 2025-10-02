from ..base_card import Card, CardCost, CardStats, CardType


class Church(Card):
    """Duration trasher that sets cards aside."""

    def __init__(self):
        super().__init__(
            name="Church",
            cost=CardCost(coins=3),
            stats=CardStats(actions=1),
            types=[CardType.ACTION, CardType.DURATION],
        )
        self.duration_persistent = False
        self.set_aside: list = []

    def play_effect(self, game_state):
        player = game_state.current_player
        choices = list(player.hand)
        selected = player.ai.choose_cards_to_set_aside_for_church(
            game_state, player, choices, 3
        )
        selected = [card for card in selected if card in player.hand][:3]
        for card in selected:
            player.hand.remove(card)
        self.set_aside = selected
        if selected:
            self.duration_persistent = True
            if self not in player.duration:
                player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        player.hand.extend(self.set_aside)
        self.set_aside = []
        to_trash = player.ai.choose_church_trash(game_state, player)
        if to_trash and to_trash in player.hand:
            player.hand.remove(to_trash)
            game_state.trash_card(player, to_trash)
        self.duration_persistent = False

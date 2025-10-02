from ..base_card import Card, CardCost, CardStats, CardType


class Captain(Card):
    def __init__(self):
        super().__init__(
            name="Captain",
            cost=CardCost(coins=6),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.DURATION, CardType.COMMAND],
        )
        self.duration_persistent = True

    def play_effect(self, game_state):
        player = game_state.current_player
        self._play_supply_action(game_state, player)
        if self not in player.duration:
            player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        self._play_supply_action(game_state, player)
        self.duration_persistent = False

    def _play_supply_action(self, game_state, player):
        from ..registry import get_card

        choices = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            try:
                card = get_card(name)
            except ValueError:
                continue
            if not card.is_action or card.is_duration or card.is_command:
                continue
            if card.cost.coins > 4:
                continue
            choices.append(card)
        if not choices:
            return
        selection = player.ai.choose_action(game_state, choices + [None])
        if not selection:
            return
        proxy = get_card(selection.name)
        player.in_play.append(proxy)
        proxy.on_play(game_state)
        if proxy in player.in_play:
            player.in_play.remove(proxy)

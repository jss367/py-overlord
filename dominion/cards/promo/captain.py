from ..base_card import Card, CardCost, CardStats, CardType

class Captain(Card):
    """Command card that plays Actions from the Supply now and next turn."""

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
        self._play_from_supply(game_state, player)
        if self not in player.duration:
            player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        self._play_from_supply(game_state, player)
        if self not in player.duration:
            player.duration.append(self)

    def _play_from_supply(self, game_state, player):
        candidates = []
        from ..registry import get_card

        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            try:
                card = get_card(name)
            except ValueError:
                continue
            if not card.is_action:
                continue
            if card.is_duration or card.is_command:
                continue
            if card.cost.coins > 4 or card.cost.potions or card.cost.debt:
                continue
            candidates.append(card)
        if not candidates:
            return
        choice = player.ai.choose_action(game_state, candidates + [None])
        if choice is None or choice.name not in {card.name for card in candidates}:
            choice = candidates[0]
        temp = get_card(choice.name)
        player.in_play.append(temp)
        temp.on_play(game_state)
        if temp in player.in_play:
            player.in_play.remove(temp)

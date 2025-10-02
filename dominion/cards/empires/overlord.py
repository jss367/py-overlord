from ..base_card import Card, CardCost, CardStats, CardType


class Overlord(Card):
    """Play another Action card from the supply costing up to 5 coins."""

    def __init__(self):
        super().__init__(
            name="Overlord",
            cost=CardCost(debt=8),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        from ..registry import get_card

        choices = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            try:
                card = get_card(name)
            except ValueError:
                continue
            if card.is_action and card.cost.coins <= 5:
                choices.append(card)
        if not choices:
            return
        proxy = player.ai.choose_action(game_state, choices + [None])
        if proxy is None:
            proxy = choices[0]
        temp_card = get_card(proxy.name)
        player.in_play.append(temp_card)
        temp_card.on_play(game_state)
        if temp_card in player.in_play:
            player.in_play.remove(temp_card)

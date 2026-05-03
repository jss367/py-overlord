"""Tools from the Plunder expansion."""

from ..base_card import Card, CardCost, CardStats, CardType


class Tools(Card):
    """$5 Action: Gain a copy of a card any player has in play."""

    def __init__(self):
        super().__init__(
            name="Tools",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player

        seen_names = set()
        candidates = []
        for p in game_state.players:
            for card in list(p.in_play) + list(p.duration):
                if card.name in seen_names:
                    continue
                if game_state.supply.get(card.name, 0) <= 0:
                    continue
                seen_names.add(card.name)
                candidates.append(get_card(card.name))

        if not candidates:
            return

        choice = player.ai.choose_buy(game_state, list(candidates) + [None])
        if choice is None or choice.name not in seen_names:
            choice = candidates[0]

        if game_state.supply.get(choice.name, 0) <= 0:
            return

        game_state.supply[choice.name] -= 1
        game_state.gain_card(player, choice)

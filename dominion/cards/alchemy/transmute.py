"""Transmute - Action from Alchemy."""

from ..base_card import Card, CardCost, CardStats, CardType


class Transmute(Card):
    """Action (P): Trash a card from your hand. If it is an...
    Action card: gain a Duchy.
    Treasure card: gain a Transmute.
    Victory card: gain a Gold.

    Multi-type cards trigger every applicable clause.
    """

    def __init__(self):
        super().__init__(
            name="Transmute",
            cost=CardCost(coins=0, potions=1),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        if not player.hand:
            return
        target = player.ai.choose_card_to_trash(game_state, list(player.hand))
        if target is None or target not in player.hand:
            return

        is_action = target.is_action
        is_treasure = target.is_treasure
        is_victory = target.is_victory

        player.hand.remove(target)
        game_state.trash_card(player, target)

        def _try_gain(name: str) -> None:
            if game_state.supply.get(name, 0) <= 0:
                return
            game_state.supply[name] -= 1
            game_state.gain_card(player, get_card(name))

        if is_action:
            _try_gain("Duchy")
        if is_treasure:
            _try_gain("Transmute")
        if is_victory:
            _try_gain("Gold")

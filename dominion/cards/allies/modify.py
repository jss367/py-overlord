from ..base_card import Card, CardCost, CardStats, CardType


class Modify(Card):
    """Trash, then cycle or gain up to $2 more."""

    def __init__(self):
        super().__init__(
            name="Modify",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        from ._rules import (
            candidates,
            effective_cost,
            gain,
            plus_cards,
            select_modes,
            trash_from_hand,
        )

        p = game_state.current_player
        card = trash_from_hand(game_state, p)
        limit = effective_cost(game_state, card) if card else None
        if limit is not None:
            limit.coins += 2
        choices = candidates(game_state, limit) if limit else []
        preferred = p.ai.choose_buy(game_state, choices + [None]) if choices else None
        for mode in select_modes(
            game_state,
            p,
            self,
            ["cycle", "gain"],
            ["gain" if preferred in choices and preferred else "cycle"],
        ):
            if mode == "cycle":
                plus_cards(game_state, p, 1)
                if not p.ignore_action_bonuses:
                    p.actions += 1
            elif limit is not None:
                gain(game_state, p, candidates(game_state, limit))

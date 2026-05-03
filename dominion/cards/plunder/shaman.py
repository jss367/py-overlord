"""Shaman from the Plunder expansion."""

from ..base_card import Card, CardCost, CardStats, CardType


class Shaman(Card):
    """$2 Action: +1 Action, +$1.

    Setup: at the start of each of your turns, you may gain a card from the
    trash costing up to $6 (this is enforced by the game engine when Shaman
    is in the kingdom — see ``GameState.handle_start_phase``).
    """

    def __init__(self):
        super().__init__(
            name="Shaman",
            cost=CardCost(coins=2),
            stats=CardStats(actions=1, coins=1),
            types=[CardType.ACTION],
        )

    @staticmethod
    def resolve_start_of_turn(game_state, player) -> None:
        """Apply the Shaman start-of-turn rule for ``player``.

        If the trash contains any cards costing up to $6, let the player
        choose one to gain (or skip).
        """

        candidates = [c for c in game_state.trash if c.cost.coins <= 6]
        if not candidates:
            return

        choice = player.ai.choose_action(
            game_state, list(candidates) + [None]
        )
        if choice is None or choice not in game_state.trash:
            return

        game_state.trash.remove(choice)
        game_state.gain_card(player, choice, from_supply=False)

"""Treasurer: Action ($5). +$3.

Choose one: trash a Treasure from your hand; gain a Treasure from the
trash to your hand; or take the Key artifact.
"""

from ..base_card import Card, CardCost, CardStats, CardType


class Treasurer(Card):
    def __init__(self) -> None:
        super().__init__(
            name="Treasurer",
            cost=CardCost(coins=5),
            stats=CardStats(coins=3),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        from ..allies._rules import choose_gain, select_modes, trash_from_hand

        player = game_state.current_player
        key = game_state.artifacts.get("Key")
        default = (
            "key"
            if key is not None and key.holder is not player
            else "gain"
            if any(c.is_treasure for c in game_state.trash)
            else "trash"
        )
        for mode in select_modes(
            game_state, player, self, ["trash", "gain", "key"], [default]
        ):
            if mode == "trash":
                trash_from_hand(
                    game_state, player, [c for c in player.hand if c.is_treasure]
                )
            elif mode == "gain":
                choice = choose_gain(
                    game_state, player, [c for c in game_state.trash if c.is_treasure]
                )
                if choice is not None:
                    game_state.trash.remove(choice)
                    game_state.gain_card(
                        player, choice, from_supply=False, to_hand=True
                    )
            elif key is not None:
                game_state.take_artifact(player, "Key")

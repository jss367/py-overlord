"""Implementation of the Vassal card."""

from ..base_card import Card, CardCost, CardStats, CardType


class Vassal(Card):
    """Action ($3): +$2.

    Discard the top card of your deck. If it's an Action, you may play it.
    """

    def __init__(self):
        super().__init__(
            name="Vassal",
            cost=CardCost(coins=3),
            stats=CardStats(coins=2),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        if not player.deck and player.discard:
            player.shuffle_discard_into_deck()
        if not player.deck:
            return

        top = player.deck.pop()

        # Non-action: discard and stop.
        if not top.is_action:
            game_state.discard_card(player, top)
            game_state.log_callback(
                (
                    "action",
                    player.ai.name,
                    f"discards {top} via Vassal",
                    {"discarded": top.name},
                )
            )
            return

        # Action: ask the AI whether to play it. Vassal does not consume an
        # action when it does so. By default the AI plays the revealed Action
        # whenever possible (it's strictly free value).
        play_it = player.ai.should_play_vassal_action(game_state, player, top)
        if not play_it:
            game_state.discard_card(player, top)
            game_state.log_callback(
                (
                    "action",
                    player.ai.name,
                    f"discards {top} via Vassal",
                    {"discarded": top.name},
                )
            )
            return

        # Move the card to in_play and play it. Vassal's bonus play does NOT
        # use up an Action and does fire on-play hooks (Prophecy etc.).
        player.in_play.append(top)
        top.on_play(game_state)
        game_state.fire_prophecy_action_hooks(player, top)
        game_state.log_callback(
            (
                "action",
                player.ai.name,
                f"plays {top} via Vassal",
                {"card": top.name},
            )
        )

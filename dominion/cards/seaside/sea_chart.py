"""Implementation of the Sea Chart card (Seaside, 2nd edition)."""

from ..base_card import Card, CardCost, CardStats, CardType


class SeaChart(Card):
    """Action ($3): +1 Card, +1 Action.

    Reveal the top card of your deck. Put it into your hand if you don't
    have a copy of it in play.
    """

    def __init__(self):
        super().__init__(
            name="Sea Chart",
            cost=CardCost(coins=3),
            stats=CardStats(cards=1, actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        # Refill from discard if needed before peeking the top of the deck.
        if not player.deck and player.discard:
            player.shuffle_discard_into_deck()
        if not player.deck:
            return

        # In this codebase ``deck[-1]`` is the top of the deck (drawn first
        # via ``deck.pop()``); ``deck[0]`` is the bottom.
        top = player.deck[-1]

        # "Reveal the top card of your deck" — log the reveal.
        game_state.log_callback(
            (
                "action",
                player.ai.name,
                f"reveals {top.name} from the top of the deck",
                {"revealed": top.name},
            )
        )

        # "Put it into your hand if you don't have a copy of it in play."
        # Sea Chart itself counts as "in play", so revealing another Sea
        # Chart fails the condition. Any non-matching card is put into hand.
        # Duration cards remain "in play" while sitting in ``player.duration``
        # (and ``player.multiplied_durations`` when re-played by Throne-style
        # effects), so include those zones in the check.
        in_play_zones = (
            player.in_play,
            player.duration,
            player.multiplied_durations,
        )
        has_copy_in_play = any(
            c.name == top.name for zone in in_play_zones for c in zone
        )
        if not has_copy_in_play:
            player.deck.pop()
            player.hand.append(top)
            game_state.log_callback(
                (
                    "action",
                    player.ai.name,
                    f"puts revealed {top.name} into hand",
                    {},
                )
            )

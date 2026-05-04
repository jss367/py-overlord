from ..base_card import Card, CardCost, CardStats, CardType


class Tiara(Card):
    """Treasure ($4): +1 Buy. While this is in play, when you gain a card,
    you may put it onto your deck. Once per turn, when you play a Treasure,
    you may play it again.

    The two "while in play" effects are wired in :mod:`game_state`:

    * Topdeck-on-gain — see ``GameState.gain_card`` (checks for Tiara in play
      and asks ``AI.should_topdeck_with_tiara``).
    * Replay-treasure-once — see ``GameState.handle_treasure_phase`` (gated by
      ``player.tiara_replay_used`` which resets each turn).
    """

    def __init__(self):
        super().__init__(
            name="Tiara",
            cost=CardCost(coins=4),
            stats=CardStats(buys=1),
            types=[CardType.TREASURE],
        )

    def play_effect(self, game_state):
        # All work happens in GameState hooks.
        pass

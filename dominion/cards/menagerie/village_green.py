"""Village Green - Action-Reaction-Duration from Menagerie."""

from ..base_card import Card, CardCost, CardStats, CardType


class VillageGreen(Card):
    """Now or next turn: +1 Card, +2 Actions; may play when discarded."""

    def __init__(self):
        super().__init__(
            name="Village Green",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.REACTION, CardType.DURATION],
        )

    def play_effect(self, game_state):
        from dominion.ways.chameleon import chameleon_plus_cards

        player = game_state.current_player
        if player.ai.should_play_village_green_now(game_state, player):
            chameleon_plus_cards(game_state, player, 1)
            if not player.ignore_action_bonuses:
                player.actions += 2
        else:
            # The duration queue stores one entry per play, including replays.
            player.duration.append(self)
            self.duration_persistent = True

    def react_to_discard(self, game_state, player) -> None:
        # Playing the reaction moves it out of discard before drawing. Leaving
        # it there can repeatedly reshuffle it during discard-down attacks.
        # The shared helper also offers Ways and handles off-turn ownership.
        if self in player.discard:
            game_state.play_action_from_zone_indirectly(player, self, player.discard)

    def on_duration(self, game_state):
        player = game_state.current_player
        game_state.draw_cards(player, 1)
        player.actions += 2
        self.duration_persistent = False

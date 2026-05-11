from ..base_card import Card, CardCost, CardStats, CardType


class Shop(Card):
    """+1 Card / +$1. You may play an Action card from your hand that you
    don't have a copy of in play."""

    def __init__(self):
        super().__init__(
            name="Shop",
            cost=CardCost(coins=3),
            stats=CardStats(cards=1, coins=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        # "In play" includes Duration cards still resolving on the player's
        # mat (engine stores those in ``player.duration``) as well as the
        # current contents of ``in_play``. Shop itself counts as a copy in
        # play (the engine moves it to ``in_play`` before resolving its
        # play effect), so a second Shop in hand is excluded too.
        in_play_action_names = {
            c.name for c in player.in_play if c.is_action
        } | {
            c.name for c in player.duration if c.is_action
        }
        playable = [
            c for c in player.hand
            if c.is_action and c.name not in in_play_action_names
        ]
        if not playable:
            return

        choice = player.ai.choose_action(game_state, playable + [None])
        if choice is None or choice not in player.hand:
            return

        player.hand.remove(choice)
        player.in_play.append(choice)
        # Route through the indirect-play helper so all the bookkeeping
        # (actions_this_turn, prophecy hooks, ally on-play hooks, tavern
        # "action_played" triggers, Citadel replay) fires correctly.
        game_state.play_action_indirectly(player, choice)

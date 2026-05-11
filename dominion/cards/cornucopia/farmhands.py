from ..base_card import Card, CardCost, CardStats, CardType


class Farmhands(Card):
    """+1 Card / +2 Actions. At the start of your next turn, you may play
    a non-Duration Action or Treasure from your hand. When you gain this,
    set aside an Action or Treasure from your hand costing up to $4; play
    it at the start of your next turn."""

    def __init__(self):
        super().__init__(
            name="Farmhands",
            cost=CardCost(coins=4),
            stats=CardStats(cards=1, actions=2),
            types=[CardType.ACTION, CardType.DURATION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        player.duration.append(self)
        self.duration_persistent = True

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)
        eligible = [
            c for c in player.hand
            if (c.is_action or c.is_treasure) and c.cost.coins <= 4
            and c.cost.potions == 0 and c.cost.debt == 0
        ]
        if not eligible:
            return
        chooser = getattr(player.ai, "choose_card_to_set_aside_for_farmhands", None)
        if chooser is None:
            choice = eligible[0]
        else:
            choice = chooser(game_state, player, list(eligible))
            if choice is None:
                return
        if choice not in player.hand:
            return
        player.hand.remove(choice)
        player.farmhands_set_aside.append(choice)

    def on_duration(self, game_state):
        player = game_state.current_player
        # NOTE: the on-gain set-aside queue is drained at the start of every
        # turn by GameState._resolve_farmhands_set_aside, independent of
        # whether a Farmhands is in duration. The duration ability below is
        # the printed "may play a non-Duration Action or Treasure from hand"
        # half of the card.

        # May play a non-Duration Action or Treasure from hand.
        playable = [
            c for c in player.hand
            if (c.is_action or c.is_treasure) and not c.is_duration
        ]
        if playable:
            choice = None
            actions = [c for c in playable if c.is_action]
            treasures = [c for c in playable if c.is_treasure and not c.is_action]
            if actions:
                choice = player.ai.choose_action(game_state, actions + [None])
            if choice is None and treasures:
                choice = player.ai.choose_treasure(game_state, treasures + [None])
            if choice is not None and choice in player.hand:
                player.hand.remove(choice)
                player.in_play.append(choice)
                if choice.is_action:
                    game_state.play_action_indirectly(player, choice)
                else:
                    choice.on_play(game_state)
                    game_state.fire_ally_play_hooks(player, choice)

        self.duration_persistent = False

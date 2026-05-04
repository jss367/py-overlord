"""Black Cat - Action-Attack-Reaction from Menagerie."""

from ..base_card import Card, CardCost, CardStats, CardType


class BlackCat(Card):
    """+2 Cards. When another player gains a Victory card you may play this
    from your hand. When played on a turn that is not yours, each other
    player gains a Curse.
    """

    def __init__(self):
        super().__init__(
            name="Black Cat",
            cost=CardCost(coins=2),
            stats=CardStats(cards=2),
            types=[CardType.ACTION, CardType.ATTACK, CardType.REACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        # If played outside owner's turn (current_player doesn't own this play),
        # then attack: each *other* player gains a Curse. We model that by
        # checking if this card was played outside the action phase via
        # the special "off_turn_play" marker set when reacted out of turn.
        if not getattr(self, "_off_turn_play", False):
            return

        from ..registry import get_card

        for other in game_state.players:
            if other is player:
                continue

            def attack_target(target):
                if game_state.supply.get("Curse", 0) <= 0:
                    return
                game_state.give_curse_to_player(target)

            game_state.attack_player(
                other, attack_target, attacker=player, attack_card=self
            )
        self._off_turn_play = False

    def on_opponent_gain(self, game_state, player, gainer, gained_card) -> None:
        """Owner reaction: when another player gains a Victory card, owner
        may play this Black Cat from hand. ``player`` here is the Black Cat
        owner. ``gainer`` is the other player who just gained a card.
        """
        if not gained_card.is_victory:
            return
        if self not in player.hand:
            return
        if not player.ai.should_react_with_black_cat(game_state, player, gainer, gained_card):
            return

        # Move from hand to in_play and resolve as an out-of-turn play.
        player.hand.remove(self)
        player.in_play.append(self)
        # Mark for play_effect to know this is the off-turn case
        self._off_turn_play = True

        # Temporarily switch current player so attack_player resolves vs. others
        original_index = game_state.current_player_index
        try:
            game_state.current_player_index = game_state.players.index(player)
            # Owner draws +2 from base on_play
            self.on_play(game_state)
        finally:
            game_state.current_player_index = original_index

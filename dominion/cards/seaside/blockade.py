from ..base_card import Card, CardCost, CardStats, CardType


class Blockade(Card):
    """Action-Duration-Attack ($4): Gain a card costing up to $4, setting it aside.
    At the start of your next turn, put it into your hand. While this is in play,
    when another player gains a copy of that card, they gain a Curse.
    """

    def __init__(self):
        super().__init__(
            name="Blockade",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.ATTACK, CardType.DURATION],
        )
        self.set_aside = None
        self.watched_card_name = None
        # Identities (object id) of opponents who weren't immune at play time.
        self._affected_player_ids: set[int] = set()

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player

        # Resolve the attack at play time so Moat / Lighthouse / Shield can
        # exempt opponents from the deferred-curse trigger for this Blockade.
        self._affected_player_ids = set()

        def attack_target(target):
            self._affected_player_ids.add(id(target))

        for other in game_state.players:
            if other is player:
                continue
            game_state.attack_player(other, attack_target)

        choice = player.ai.choose_card_to_gain_with_blockade(game_state, player, max_cost=4)
        if choice is None:
            return

        if game_state.supply.get(choice.name, 0) <= 0:
            return

        game_state.supply[choice.name] -= 1
        gained = game_state.gain_card(player, get_card(choice.name))

        # Set aside only if the card still resides in discard/deck. If another
        # ability (e.g. Sailor playing a gained Duration) has already moved it
        # elsewhere, leave it where it is — otherwise the same Card object
        # would end up in multiple zones when Blockade resolves next turn.
        if gained in player.discard:
            player.discard.remove(gained)
            self.set_aside = gained
        elif gained in player.deck:
            player.deck.remove(gained)
            self.set_aside = gained

        # Always watch the pile name so opponents who gain a copy still get
        # cursed (the watch effect is independent of where our copy went).
        self.watched_card_name = gained.name
        player.duration.append(self)
        self.duration_persistent = True

    def on_duration(self, game_state):
        player = game_state.current_player
        if self.set_aside is not None:
            player.hand.append(self.set_aside)
            self.set_aside = None
        # Stop watching for opponent gains; clear watch.
        self.watched_card_name = None
        self.duration_persistent = False

    def on_opponent_gain(self, game_state, owner, gainer, gained_card):
        """Curse opponents who gain a matching card while this is in play.

        Only opponents who were actually hit by the original Attack play (i.e.
        not protected by Moat/Lighthouse/Shield at play time) are subject to
        the follow-up curse trigger.
        """
        if self.watched_card_name is None:
            return
        if self not in owner.duration:
            return
        if gained_card.name != self.watched_card_name:
            return
        if id(gainer) not in self._affected_player_ids:
            return
        if game_state.supply.get("Curse", 0) <= 0:
            return
        game_state.give_curse_to_player(gainer)

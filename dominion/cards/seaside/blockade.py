from ..base_card import Card, CardCost, CardStats, CardType


class Blockade(Card):
    """Action-Duration-Attack ($4): Gain a card costing up to $4, setting it aside.
    At the start of your next turn, put it into your hand. While that card is
    set aside, opponents gaining a copy on their own turn gain a Curse.
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
        affected = set()

        def attack_target(target):
            affected.add(id(target))

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
        actual_gain = []
        game_state.gain_card(player, get_card(choice.name), gain_observer=actual_gain.append)
        if not actual_gain:
            return
        gained = actual_gain[0]
        # Set aside only the actual gain if no earlier effect moved it.
        if not game_state._remove_gained_card_from_zones(player, gained):
            return
        self.set_aside = gained

        self.watched_card_name = gained.name
        self._affected_player_ids = affected
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
        """Curse affected opponents while the matching card remains set aside.

        Only opponents who were actually hit by the original Attack play (i.e.
        not protected by Moat/Lighthouse/Shield at play time) are subject to
        the follow-up curse trigger.
        """
        if (self.set_aside is None or self.watched_card_name is None
                or getattr(self.set_aside, "returned_to_supply", False)
                or self.set_aside.name != self.watched_card_name):
            return
        if self not in owner.duration:
            return
        if gained_card.name != self.watched_card_name:
            return
        if gainer is not game_state.turn_player:
            return
        if id(gainer) not in self._affected_player_ids:
            return
        if game_state.supply.get("Curse", 0) <= 0:
            return
        game_state.give_curse_to_player(gainer)

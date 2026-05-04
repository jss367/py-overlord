from ..base_card import Card, CardCost, CardStats, CardType


class Sailor(Card):
    """Action-Duration ($4): +1 Action. Once this turn, when you gain a card other
    than this, you may play it. At the start of your next turn, +$2 and you may
    trash a card from your hand.
    """

    def __init__(self):
        super().__init__(
            name="Sailor",
            cost=CardCost(coins=4),
            stats=CardStats(actions=1),
            types=[CardType.ACTION, CardType.DURATION],
        )
        self.duration_persistent = True

    def play_effect(self, game_state):
        player = game_state.current_player
        # Each Sailor played grants one "play a non-Sailor gain this turn" use.
        player.sailor_play_uses = getattr(player, "sailor_play_uses", 0) + 1
        player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        player.coins += 2

        # Optionally trash a card from hand.
        if player.hand:
            choice = player.ai.choose_sailor_trash(game_state, player, list(player.hand))
            if choice is not None and choice in player.hand:
                player.hand.remove(choice)
                game_state.trash_card(player, choice)

        self.duration_persistent = False

    def on_gain_for_owner(self, game_state, owner, gained_card):
        """Called by gain_card to allow Sailor to play a freshly gained Duration.

        Sailor's text is "Once this turn, when you gain a Duration card other
        than this, play it." Returns True if the gain was played (and consumed
        a Sailor use).
        """
        if gained_card.name == "Sailor":
            return False
        if not gained_card.is_duration:
            return False
        if getattr(owner, "sailor_play_uses", 0) <= 0:
            return False
        if not owner.ai.should_play_gain_with_sailor(game_state, owner, gained_card):
            return False

        owner.sailor_play_uses -= 1

        # Move the gained card from discard/deck into in_play, then play it.
        if gained_card in owner.discard:
            owner.discard.remove(gained_card)
        elif gained_card in owner.deck:
            owner.deck.remove(gained_card)
        else:
            return False

        owner.in_play.append(gained_card)
        gained_card.on_play(game_state)
        game_state.fire_ally_play_hooks(owner, gained_card)
        return True

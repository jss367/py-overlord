from ..base_card import Card, CardCost, CardStats, CardType


class FirstMate(Card):
    """Implementation of the First Mate card from the Plunder expansion."""

    def __init__(self):
        # According to the Dominion Strategy wiki the card costs 5 Coins and is
        # a simple Action card (no Duration type).
        super().__init__(
            name="First Mate",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        # Determine all Action cards currently in hand.
        actions_in_hand = [c for c in player.hand if c.is_action]
        if not actions_in_hand:
            # No Action cards to play, just draw up to six.
            self._draw_to_six(game_state, player)
            return

        # Allow the AI to choose an Action card to play copies of.  Passing None
        # lets the AI decide to skip playing any card if desired.
        choice = player.ai.choose_action(game_state, actions_in_hand + [None])
        if choice is None:
            self._draw_to_six(game_state, player)
            return

        chosen_name = choice.name

        # Play copies of the chosen card, letting the AI decide after each play
        # whether to continue.  Newly drawn copies remain eligible to be played
        # on subsequent iterations.
        first_iteration = True
        while True:
            matching_cards = [c for c in player.hand if c.name == chosen_name]
            if not matching_cards:
                break

            if first_iteration:
                card_to_play = matching_cards[0]
                first_iteration = False
            else:
                card_to_play = player.ai.choose_action(
                    game_state, matching_cards + [None]
                )
                if card_to_play is None:
                    break

            player.hand.remove(card_to_play)
            player.in_play.append(card_to_play)
            card_to_play.on_play(game_state)

        self._draw_to_six(game_state, player)

    @staticmethod
    def _draw_to_six(game_state, player):
        """Helper to draw until the player has six cards in hand."""
        while len(player.hand) < 6:
            if not player.deck and not player.discard:
                break
            game_state.draw_cards(player, 1)

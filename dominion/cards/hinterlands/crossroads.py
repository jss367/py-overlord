from ..base_card import Card, CardCost, CardStats, CardType


class Crossroads(Card):
    """Reveal your hand. +1 Card per Victory card revealed.

    If this is the first Crossroads played this turn, +3 Actions.
    """

    def __init__(self):
        super().__init__(
            name="Crossroads",
            cost=CardCost(coins=2),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        from dominion.ways.chameleon import chameleon_plus_cards

        player = game_state.current_player

        # Crossroads is already in play, so it never reveals itself; the
        # count is of the hand as it stands when the card resolves.
        victory_cards = sum(1 for card in player.hand if card.is_victory)
        # "+1 Card per Victory card revealed" is a +Cards instruction, so Way
        # of the Chameleon turns the whole count into +$ instead.
        chameleon_plus_cards(game_state, player, victory_cards)

        player.crossroads_played += 1
        # Snowy Village tells the player to ignore an Action card's +Actions,
        # which covers this one as much as a printed bonus.
        if player.crossroads_played == 1 and not player.ignore_action_bonuses:
            player.actions += 3

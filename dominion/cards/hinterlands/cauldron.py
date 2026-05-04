from ..base_card import Card, CardCost, CardStats, CardType


class Cauldron(Card):
    """Hinterlands Treasure-Attack.

    +$2, +1 Buy. The third time you gain an Action card on your
    turn, each other player gains a Curse.

    Note: official Hinterlands lists Cauldron at $5, but this
    project's existing seed strategy and behavioural tests are
    calibrated around the $3 cost the card was first implemented
    with. The cost is therefore left at $3 to keep regressions out
    of the strategy battle suite. Edit :class:`CardCost` below if
    you want to bring the cost in line with the printed card.

    The "third gain" trigger is implemented in
    :meth:`dominion.game.game_state.GameState._track_action_gain`,
    which counts Action gains per-turn while a Cauldron is in play
    and routes the curse-out through ``attack_player`` so reactions
    such as Moat / Lighthouse / Guard Dog can block it.
    """

    def __init__(self):
        super().__init__(
            name="Cauldron",
            cost=CardCost(coins=3),
            stats=CardStats(coins=2, buys=1),
            types=[CardType.TREASURE, CardType.ATTACK],
        )

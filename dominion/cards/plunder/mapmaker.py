"""Mapmaker from the Plunder expansion."""

from ..base_card import Card, CardCost, CardStats, CardType


class Mapmaker(Card):
    """$4 Action-Reaction.

    Look at the top 4 cards of your deck. Put 2 into your hand, discard the
    rest.

    When another player gains a Victory card, you may reveal this from your
    hand to perform the same effect (look at top 4, take 2, discard rest).
    """

    def __init__(self):
        super().__init__(
            name="Mapmaker",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.REACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        self._do_dig(game_state, player)

    def on_card_gained(self, game_state, owner, gainer, gained_card):
        # Reaction only applies when this Mapmaker is in *another* player's hand
        # (not in_play). on_card_gained's dispatcher only iterates in_play and
        # duration zones, so this hook is never called when in hand. Use the
        # explicit hand-reaction hook below instead.
        return

    def react_to_opponent_victory_gain(self, game_state, player, gained_card):
        if not gained_card.is_victory:
            return
        if self not in player.hand:
            return
        if not player.ai.should_react_with_mapmaker(
            game_state, player, game_state.current_player, gained_card
        ):
            return

        game_state.log_callback(
            (
                "action",
                player.ai.name,
                f"reveals Mapmaker reacting to {gained_card.name}",
                {},
            )
        )
        self._do_dig(game_state, player)

    @staticmethod
    def _do_dig(game_state, player):
        revealed = []
        for _ in range(4):
            if not player.deck and player.discard:
                player.shuffle_discard_into_deck()
            if not player.deck:
                break
            revealed.append(player.deck.pop())

        if not revealed:
            return

        keep_count = min(2, len(revealed))

        chosen: list = []
        remaining = list(revealed)
        for _ in range(keep_count):
            if not remaining:
                break
            pick = player.ai.choose_action(game_state, list(remaining) + [None])
            if pick is None or pick not in remaining:
                pick = remaining[0]
            remaining.remove(pick)
            chosen.append(pick)

        for card in chosen:
            player.hand.append(card)

        for card in remaining:
            game_state.discard_card(player, card)

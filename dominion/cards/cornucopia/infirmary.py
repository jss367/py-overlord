from ..base_card import Card, CardCost, CardStats, CardType


class Infirmary(Card):
    """+1 Card. You may trash a card from your hand. Overpay: +1 Play of
    this card per $1 overpaid."""

    def __init__(self):
        super().__init__(
            name="Infirmary",
            cost=CardCost(coins=3),
            stats=CardStats(cards=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        if not player.hand:
            return
        choice = player.ai.choose_card_to_trash(
            game_state, list(player.hand) + [None]
        )
        if choice is None or choice not in player.hand:
            return
        player.hand.remove(choice)
        game_state.trash_card(player, choice)

    def may_overpay(self, game_state) -> bool:
        return True

    def on_overpay(self, game_state, player, amount: int) -> None:
        # Each $1 overpaid plays this card. The buy flow has just put the
        # gained Infirmary into ``player.discard``. Move it into play before
        # replaying so that effects which inspect the in-play zone (and any
        # mid-replay shuffle that would otherwise re-include this card) see
        # it correctly. It stays in play through cleanup, where it will be
        # discarded normally.
        if amount <= 0:
            return
        if self in player.discard:
            player.discard.remove(self)
            player.in_play.append(self)
        for _ in range(amount):
            self.on_play(game_state)

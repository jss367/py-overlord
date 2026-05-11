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

    def on_overpay(
        self, game_state, player, amount: int, gained_card=None
    ) -> None:
        # Each $1 overpaid plays this card. The buy flow passes the actual
        # gained instance via ``gained_card`` — that may be ``self`` (the
        # freshly-bought card) or a different Infirmary reclaimed from the
        # Exile mat by ``gain_card``. The gained card is normally in
        # ``player.discard``, but topdeck-on-gain effects (Royal Seal,
        # Watchtower topdeck, Tiara, Travelling Fair, ...) can have moved
        # it onto the deck or into hand by the time this hook fires, and
        # Watchtower trash sends it to the trash. Move it from whichever
        # zone holds it into play before replaying so the in-play zone
        # reflects the card actually being played and a mid-replay shuffle
        # cannot re-include it via the discard pile.
        if amount <= 0:
            return
        target = gained_card if gained_card is not None else self
        # Trader's reaction can substitute a Silver for the gained Infirmary
        # (``gain_card`` returns the substituted card). In that case the
        # player no longer owns a freshly-gained Infirmary to play.
        if target.name != self.name:
            return
        for zone in (player.discard, player.deck, player.hand):
            if target in zone:
                zone.remove(target)
                break
        else:
            # Card was redirected to trash/exile/elsewhere. Don't try to
            # play it from there — silently drop the replays. (Per Donald
            # X, an Infirmary that was Watchtower-trashed before overpay
            # resolves cannot be played.)
            return
        player.in_play.append(target)
        for _ in range(amount):
            game_state.play_action_indirectly(player, target)

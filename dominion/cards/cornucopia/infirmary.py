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
        # Each $1 overpaid plays this card. The gained Infirmary is normally
        # in ``player.discard`` after the buy, but topdeck-on-gain effects
        # (Royal Seal, Watchtower topdeck, Tiara, Travelling Fair, ...) can
        # have already moved it onto the deck or into hand by the time this
        # hook fires. Watchtower trash sends it to the trash. We also need
        # to handle the Exile-reclaim case: ``gain_card`` may substitute a
        # different Infirmary instance (the one reclaimed from Exile) for
        # ``self``, so we search by name across the player's zones rather
        # than for the exact ``self`` reference. Move that Infirmary into
        # play before replaying so the in-play zone reflects the card
        # actually being played and a mid-replay shuffle cannot re-include
        # this card via the discard pile.
        if amount <= 0:
            return
        target = None
        for zone in (player.discard, player.deck, player.hand):
            for card in zone:
                if card.name == self.name:
                    target = card
                    zone.remove(card)
                    break
            if target is not None:
                break
        if target is None:
            # Card was redirected to trash/exile/elsewhere. Don't try to
            # play it from there — silently drop the replays. (Per Donald
            # X, an Infirmary that was Watchtower-trashed before overpay
            # resolves cannot be played.)
            return
        player.in_play.append(target)
        for _ in range(amount):
            target.on_play(game_state)
            game_state.fire_ally_play_hooks(player, target)

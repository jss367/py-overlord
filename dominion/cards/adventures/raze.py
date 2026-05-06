"""Raze (Adventures) — $2 Action."""

from ..base_card import Card, CardCost, CardStats, CardType


class Raze(Card):
    def __init__(self):
        super().__init__(
            name="Raze",
            cost=CardCost(coins=2),
            stats=CardStats(actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        # Choose Raze itself (in_play) or a card from hand to trash.
        candidates: list = []
        if self in player.in_play:
            candidates.append(self)
        candidates.extend(player.hand)
        if not candidates:
            return
        target = player.ai.choose_card_to_raze(game_state, player, list(candidates))
        if target is None:
            return
        target_cost = target.cost.coins
        if target is self:
            if self in player.in_play:
                player.in_play.remove(self)
            game_state.trash_card(player, self)
        else:
            if target not in player.hand:
                return
            player.hand.remove(target)
            game_state.trash_card(player, target)
        # Look at top X cards.
        if target_cost <= 0:
            return
        revealed: list = []
        while len(revealed) < target_cost:
            if not player.deck and player.discard:
                player.shuffle_discard_into_deck()
            if not player.deck:
                break
            revealed.append(player.deck.pop())
        if not revealed:
            return
        keep = player.ai.choose_card_to_keep_from_raze(game_state, player, revealed)
        if keep and keep in revealed:
            revealed.remove(keep)
            player.hand.append(keep)
        for card in revealed:
            game_state.discard_card(player, card)

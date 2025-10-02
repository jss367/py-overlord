from ..base_card import Card, CardCost, CardStats, CardType


class YoungWitch(Card):
    """Draws cards and forces opponents to gain Curses unless blocked."""

    def __init__(self):
        super().__init__(
            name="Young Witch",
            cost=CardCost(coins=4),
            stats=CardStats(cards=2),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        discard_count = min(2, len(player.hand))
        if discard_count:
            choices = player.ai.choose_cards_to_discard(
                game_state, player, list(player.hand), discard_count, reason="young_witch"
            )
            chosen = []
            for card in choices:
                if card in player.hand and len(chosen) < discard_count:
                    chosen.append(card)
            if len(chosen) < discard_count:
                remaining = [card for card in player.hand if card not in chosen]
                remaining.sort(key=lambda c: (c.cost.coins, c.name))
                chosen.extend(remaining[: discard_count - len(chosen)])

            for card in chosen:
                if card in player.hand:
                    player.hand.remove(card)
                    game_state.discard_card(player, card)

        def attack_target(target):
            game_state.give_curse_to_player(target)

        for other in game_state.players:
            if other is player:
                continue
            game_state.attack_player(other, attack_target)

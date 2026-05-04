from ..base_card import Card, CardCost, CardStats, CardType


class SeaWitch(Card):
    """Action-Duration-Attack ($5): +2 Cards. Each other player gains a Curse.
    At the start of your next turn: +2 Cards, then discard 2 cards.
    """

    def __init__(self):
        super().__init__(
            name="Sea Witch",
            cost=CardCost(coins=5),
            stats=CardStats(cards=2),
            types=[CardType.ACTION, CardType.ATTACK, CardType.DURATION],
        )
        self.duration_persistent = True

    def play_effect(self, game_state):
        player = game_state.current_player

        def curse_target(target):
            if game_state.supply.get("Curse", 0) > 0:
                game_state.give_curse_to_player(target)

        for other in game_state.players:
            if other is player:
                continue
            game_state.attack_player(other, curse_target)

        player.duration.append(self)
        self.duration_persistent = True

    def on_duration(self, game_state):
        player = game_state.current_player
        game_state.draw_cards(player, 2)

        to_discard = min(2, len(player.hand))
        if to_discard > 0:
            selected = player.ai.choose_cards_to_discard(
                game_state, player, list(player.hand), to_discard, reason="sea_witch"
            )

            discarded = 0
            for card in selected:
                if discarded >= to_discard:
                    break
                if card in player.hand:
                    player.hand.remove(card)
                    game_state.discard_card(player, card)
                    discarded += 1

            while discarded < to_discard and player.hand:
                card = min(
                    player.hand,
                    key=lambda c: (c.is_action, c.is_treasure, c.cost.coins, c.name),
                )
                player.hand.remove(card)
                game_state.discard_card(player, card)
                discarded += 1

        self.duration_persistent = False

from ..base_card import Card, CardCost, CardStats, CardType


class Swindler(Card):
    def __init__(self):
        super().__init__(
            name="Swindler",
            cost=CardCost(coins=3),
            stats=CardStats(coins=2),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        """Each other player trashes top card; attacker chooses same-cost replacement."""
        from ..registry import get_card

        player = game_state.current_player

        def attack_target(target):
            drawn = target.draw_cards(1)
            if not drawn:
                return
            card = drawn[0]
            target.hand.remove(card)
            trashed_cost = card.cost.coins
            game_state.trash_card(target, card)

            # Find cards in supply with the same cost
            options = []
            for name, count in game_state.supply.items():
                if count <= 0:
                    continue
                candidate = get_card(name)
                if candidate.cost.coins == trashed_cost and candidate.cost.potions == 0:
                    options.append(candidate)

            if not options:
                return

            # Attacker chooses what the target gains
            choice = player.ai.choose_buy(game_state, options)
            if choice is None or choice.name not in game_state.supply:
                # Default to worst option for opponent (Curse if available, else cheapest VP)
                choice = options[0]

            if game_state.supply.get(choice.name, 0) > 0:
                game_state.supply[choice.name] -= 1
                game_state.gain_card(target, choice)

        for other in game_state.players:
            if other is player:
                continue
            game_state.attack_player(other, attack_target)

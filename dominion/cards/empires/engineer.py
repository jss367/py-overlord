from ..base_card import Card, CardCost, CardStats, CardType


class Engineer(Card):
    def __init__(self):
        super().__init__(
            name="Engineer",
            cost=CardCost(debt=4),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        def affordable_cards() -> list[Card]:
            cards: list[Card] = []
            for _name, candidate, _count in game_state._iter_gainable_supply_cards():
                if (game_state.get_card_cost(player, candidate) <= 4
                        and candidate.cost.potions == 0 and candidate.cost.debt == 0):
                    cards.append(candidate)
            cards.sort(key=lambda c: (c.cost.coins, c.name), reverse=True)
            return cards

        def gain_from_choices(choices: list[Card]):
            if not choices:
                return None
            choice = player.ai.choose_buy(game_state, choices)
            if choice not in choices:
                choice = choices[0]
            gained = game_state.take_top_supply_card(game_state.supply_pile_key(choice.name))
            if gained is not None:
                game_state.gain_card(player, gained)
            return choice

        choices = affordable_cards()
        gain_from_choices(choices)

        if self not in player.in_play:
            return

        if not player.ai.should_trash_engineer_for_extra_gains(
            game_state, player, self
        ):
            return

        player.in_play.remove(self)
        game_state.trash_card(player, self)

        gain_from_choices(affordable_cards())

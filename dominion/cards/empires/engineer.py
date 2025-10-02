from ..base_card import Card, CardCost, CardStats, CardType


class Engineer(Card):
    def __init__(self):
        super().__init__(
            name="Engineer",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        from ..registry import get_card

        def affordable_cards() -> list[Card]:
            cards: list[Card] = []
            for name, count in game_state.supply.items():
                if count <= 0:
                    continue
                candidate = get_card(name)
                if candidate.cost.coins <= 4:
                    cards.append(candidate)
            cards.sort(key=lambda c: (c.cost.coins, c.name), reverse=True)
            return cards

        def gain_from_choices(choices: list[Card]):
            if not choices:
                return None
            choice = player.ai.choose_buy(game_state, choices)
            if choice not in choices:
                choice = choices[0]
            game_state.supply[choice.name] -= 1
            game_state.gain_card(player, choice)
            return choice

        choices = affordable_cards()
        if not choices:
            return
        gain_from_choices(choices)

        if self not in player.in_play:
            return

        if not player.ai.should_trash_engineer_for_extra_gains(
            game_state, player, self
        ):
            return

        player.in_play.remove(self)
        game_state.trash_card(player, self)

        for _ in range(2):
            extra_choices = affordable_cards()
            if not extra_choices:
                break
            gain_from_choices(extra_choices)

from ..base_card import Card, CardCost, CardStats, CardType


class Rebuild(Card):
    def __init__(self):
        super().__init__(
            name="Rebuild",
            cost=CardCost(coins=5),
            stats=CardStats(actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        named = self._choose_name(game_state, player)
        trashed = self._find_victory_to_trash(game_state, player, named)
        if not trashed:
            return

        gain_options = self._get_rebuild_gains(game_state, trashed)
        if not gain_options:
            return

        choice = player.ai.choose_buy(game_state, gain_options + [None])
        if not choice:
            return

        if game_state.supply.get(choice.name, 0) <= 0:
            return

        from ..registry import get_card

        game_state.supply[choice.name] -= 1
        game_state.gain_card(player, get_card(choice.name))

    def _choose_name(self, game_state, player) -> str:
        known_names = {card.name for card in player.all_cards()}
        known_names.update(game_state.supply.keys())
        options = sorted(known_names)
        choice = player.ai.choose_rebuild_name(game_state, player, options)
        return choice or "Province"

    def _find_victory_to_trash(self, game_state, player, forbidden: str):
        revealed: list = []
        target = None

        while True:
            if not player.deck and player.discard:
                player.shuffle_discard_into_deck()
            if not player.deck:
                break

            card = player.deck.pop()
            if card.is_victory and card.name != forbidden:
                target = card
                break
            revealed.append(card)

        for card in revealed:
            game_state.discard_card(player, card)

        if not target:
            return None

        game_state.trash_card(player, target)
        return target

    def _get_rebuild_gains(self, game_state, trashed):
        from ..registry import get_card

        max_cost = trashed.cost.coins + 3
        options = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            card = get_card(name)
            if card.is_victory and card.cost.coins <= max_cost:
                options.append(card)
        return options

from ..base_card import Card, CardCost, CardStats, CardType


class NobleBrigand(Card):
    def __init__(self):
        super().__init__(
            name="Noble Brigand",
            cost=CardCost(coins=4),
            stats=CardStats(coins=1),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        trashed = self._perform_attack(game_state, player)
        self._maybe_gain_trashed(game_state, player, trashed)

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)
        trashed = self._perform_attack(game_state, player)
        self._maybe_gain_trashed(game_state, player, trashed)

    def _perform_attack(self, game_state, attacker):
        trashed_cards = []

        from ..registry import get_card

        for target in game_state.players:
            if target is attacker:
                continue

            revealed = []
            for _ in range(2):
                if not target.deck and target.discard:
                    target.shuffle_discard_into_deck()
                if not target.deck:
                    break
                revealed.append(target.deck.pop())

            treasures = [card for card in revealed if card.name in {"Silver", "Gold"}]
            if treasures:
                to_trash = max(treasures, key=self._treasure_value)
                revealed.remove(to_trash)
                game_state.trash_card(target, to_trash)
                trashed_cards.append(to_trash)
            else:
                if game_state.supply.get("Copper", 0) > 0:
                    game_state.supply["Copper"] -= 1
                    game_state.gain_card(attacker, get_card("Copper"))

            for card in revealed:
                game_state.discard_card(target, card)

        return trashed_cards

    def _maybe_gain_trashed(self, game_state, player, trashed_cards):
        if not trashed_cards:
            return

        best = max(trashed_cards, key=self._treasure_value)
        if best in game_state.trash:
            game_state.trash.remove(best)
        game_state.discard_card(player, best)
        best.on_gain(game_state, player)

    @staticmethod
    def _treasure_value(card):
        if card.name == "Gold":
            return 2
        if card.name == "Silver":
            return 1
        return 0

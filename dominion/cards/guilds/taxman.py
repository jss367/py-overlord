from ..base_card import Card, CardCost, CardStats, CardType


class Taxman(Card):
    """Trashes a Treasure, upgrades it, and pressures opponents."""

    def __init__(self):
        super().__init__(
            name="Taxman",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        treasures = [card for card in player.hand if card.is_treasure]
        if not treasures:
            return

        trash_choice = player.ai.choose_card_to_trash(game_state, treasures + [None])
        if trash_choice is None or trash_choice not in player.hand:
            return

        player.hand.remove(trash_choice)
        game_state.trash_card(player, trash_choice)
        trashed_name = trash_choice.name

        gain_candidates = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            card = get_card(name)
            if (
                card.is_treasure
                and card.name != trashed_name
                and card.cost.coins <= trash_choice.cost.coins + 3
            ):
                gain_candidates.append(card)

        if gain_candidates:
            choice = player.ai.choose_buy(game_state, gain_candidates + [None])
            gain_names = {card.name for card in gain_candidates}
            if choice is None or choice.name not in gain_names:
                choice = max(gain_candidates, key=lambda c: (c.cost.coins, c.stats.vp, c.name))
            if game_state.supply.get(choice.name, 0) > 0:
                game_state.supply[choice.name] -= 1
                game_state.gain_card(player, choice, to_deck=True)

        def attack(target):
            if len(target.hand) < 5:
                return
            matching = [card for card in target.hand if card.name == trashed_name]
            if not matching:
                return
            card = matching[0]
            target.hand.remove(card)
            game_state.discard_card(target, card)

        for other in game_state.players:
            if other is player:
                continue
            game_state.attack_player(other, attack, attacker=player, attack_card=self)

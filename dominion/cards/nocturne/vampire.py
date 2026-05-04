"""Vampire — $5 Action-Attack-Night.

Each other player receives a Hex. Gain a card costing up to $5 (not Vampire).
Exchange this for a Bat.
"""

from ..base_card import Card, CardCost, CardStats, CardType


class Vampire(Card):
    nocturne_piles = {"Bat": 10}

    def __init__(self):
        super().__init__(
            name="Vampire",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.ATTACK, CardType.NIGHT, CardType.DOOM],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        for other in game_state.players:
            if other is player:
                continue

            def attack(target):
                game_state.give_hex_to_player(target)

            game_state.attack_player(other, attack, attacker=player, attack_card=self)

        # Gain a card up to $5 (not Vampire)
        options = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            if name == "Vampire":
                continue
            try:
                card = get_card(name)
            except ValueError:
                continue
            if card.cost.coins > 5 or card.cost.potions > 0 or card.cost.debt > 0:
                continue
            if not card.may_be_bought(game_state):
                continue
            options.append(card)
        if options:
            choice = player.ai.choose_card_to_gain_up_to(
                game_state, player, options, 5
            )
            if choice is None:
                choice = max(options, key=lambda c: (c.cost.coins, c.stats.cards, c.name))
            if game_state.supply.get(choice.name, 0) > 0:
                game_state.supply[choice.name] -= 1
                game_state.gain_card(player, choice)

        # Exchange Vampire for a Bat
        if self in player.in_play:
            player.in_play.remove(self)
        game_state.supply["Vampire"] = game_state.supply.get("Vampire", 0) + 1
        if game_state.supply.get("Bat", 0) > 0:
            game_state.supply["Bat"] -= 1
            game_state.gain_card(player, get_card("Bat"))

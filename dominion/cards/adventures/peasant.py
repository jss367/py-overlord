"""Peasant chain (Adventures): Peasant → Soldier → Fugitive → Disciple → Teacher."""

from ..base_card import Card, CardCost, CardStats, CardType


class Peasant(Card):
    next_traveller = "Soldier"

    def __init__(self):
        super().__init__(
            name="Peasant",
            cost=CardCost(coins=2),
            stats=CardStats(buys=1, coins=1),
            types=[CardType.ACTION, CardType.TRAVELLER],
        )

    def get_additional_piles(self):
        return {
            "Soldier": 5,
            "Fugitive": 5,
            "Disciple": 5,
            "Teacher": 5,
        }


class Soldier(Card):
    next_traveller = "Fugitive"

    def __init__(self):
        super().__init__(
            name="Soldier",
            cost=CardCost(coins=3),
            stats=CardStats(coins=2),
            types=[CardType.ACTION, CardType.ATTACK, CardType.TRAVELLER],
        )

    def starting_supply(self, game_state) -> int:
        return 5

    def may_be_bought(self, game_state) -> bool:
        return False

    def play_effect(self, game_state):
        player = game_state.current_player
        # +$1 per other Attack you have in play.
        attack_count = sum(
            1 for c in player.in_play if c.is_attack and c is not self
        )
        player.coins += attack_count

        def attack_target(target):
            if len(target.hand) < 4:
                return
            choices = list(target.hand)
            picks = target.ai.choose_cards_to_discard(
                game_state, target, choices, 1, reason="soldier"
            )
            if picks:
                card = picks[0]
                if card in target.hand:
                    target.hand.remove(card)
                    game_state.discard_card(target, card)
            elif target.hand:
                fallback = min(target.hand, key=lambda c: (c.cost.coins, c.name))
                target.hand.remove(fallback)
                game_state.discard_card(target, fallback)

        for other in game_state.players:
            if other is player:
                continue
            game_state.attack_player(
                other, attack_target, attacker=player, attack_card=self
            )


class Fugitive(Card):
    next_traveller = "Disciple"

    def __init__(self):
        super().__init__(
            name="Fugitive",
            cost=CardCost(coins=4),
            stats=CardStats(cards=2, actions=1),
            types=[CardType.ACTION, CardType.TRAVELLER],
        )

    def starting_supply(self, game_state) -> int:
        return 5

    def may_be_bought(self, game_state) -> bool:
        return False

    def play_effect(self, game_state):
        player = game_state.current_player
        if not player.hand:
            return
        picks = player.ai.choose_cards_to_discard(
            game_state, player, list(player.hand), 1, reason="fugitive"
        )
        if not picks:
            return
        card = picks[0]
        if card in player.hand:
            player.hand.remove(card)
            game_state.discard_card(player, card)


class Disciple(Card):
    next_traveller = "Teacher"

    def __init__(self):
        super().__init__(
            name="Disciple",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.TRAVELLER],
        )

    def starting_supply(self, game_state) -> int:
        return 5

    def may_be_bought(self, game_state) -> bool:
        return False

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        actions = [c for c in player.hand if c.is_action]
        if not actions:
            return
        chosen = player.ai.choose_disciple_action_to_replay(
            game_state, player, actions
        )
        if chosen is None or chosen not in player.hand:
            return
        if not game_state.move_card_from_hand_to_play(player, chosen):
            return
        game_state.play_action_indirectly(player, chosen)
        game_state.play_action_indirectly(player, chosen)
        if game_state.supply.get(chosen.name, 0) > 0:
            game_state.supply[chosen.name] -= 1
            game_state.gain_card(player, get_card(chosen.name))


class Teacher(Card):
    """$5 Action-Duration-Reserve.

    Put this on your Tavern mat. At the start of your turn, you may call
    this to move one of your +1 Card / +1 Action / +1 Buy / +$1 tokens to
    an Action Supply pile you have no tokens on. Calling Teacher discards
    it from the Tavern mat per the standard Reserve "call" rule (Teacher
    has no special clause overriding that default).
    """

    next_traveller = None

    def __init__(self):
        super().__init__(
            name="Teacher",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[
                CardType.ACTION,
                CardType.DURATION,
                CardType.RESERVE,
                CardType.TRAVELLER,
            ],
        )

    def starting_supply(self, game_state) -> int:
        return 5

    def may_be_bought(self, game_state) -> bool:
        return False

    def play_effect(self, game_state):
        player = game_state.current_player
        game_state.set_aside_on_tavern(player, self)

    def on_call_from_tavern(self, game_state, player, trigger, *args, **kwargs):
        if trigger != "start_of_turn":
            return False
        if not player.ai.should_call_from_tavern(
            game_state, player, self, trigger, *args
        ):
            return False
        # Find piles where this player has no token yet.
        from ..registry import get_card

        token_options = ["+1 Card", "+1 Action", "+1 Buy", "+$1"]
        # Determine which token kinds we haven't placed
        unplaced = [
            kind for kind in token_options
            if game_state.player_token_pile(player, kind) is None
        ]
        if not unplaced:
            return False
        chosen_kind = player.ai.choose_teacher_token(game_state, player, unplaced)
        if chosen_kind is None:
            return False
        # Find an Action pile this player has no token on.
        candidate_piles = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            try:
                card = get_card(name)
            except ValueError:
                continue
            if not card.is_action:
                continue
            idx = game_state.players.index(player)
            existing = game_state.pile_tokens.get((idx, name), set())
            if existing:
                continue
            candidate_piles.append(card)
        if not candidate_piles:
            return False
        target = max(
            candidate_piles,
            key=lambda c: (player.count_in_deck(c.name), c.cost.coins, c.name),
        )
        game_state.add_pile_token(player, target.name, chosen_kind)
        # Teacher is a Reserve card — calling it discards it (one token
        # placement per Teacher copy, like every other Reserve card).
        game_state.call_from_tavern(player, self)
        return True

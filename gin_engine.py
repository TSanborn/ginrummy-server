import random

RANKS = ["A","2","3","4","5","6","7","8","9","10","J","Q","K"]
SUITS = ["♠", "♥", "♦", "♣"]
RANK_VALUES = {r: i+1 for i, r in enumerate(RANKS)}

class GinGame:
    def __init__(self):
        self.scores = [0, 0]  # cumulative scores
        self.start_new_round()

    def start_new_round(self):
        self.deck = [f"{r}{s}" for s in SUITS for r in RANKS]
        random.shuffle(self.deck)

        self.hands = [[], []]
        for _ in range(10):
            self.hands[0].append(self.deck.pop())
            self.hands[1].append(self.deck.pop())

        self.discard_pile = [self.deck.pop()]
        self.turn = 0
        self.winner = None
        self.deadwood = [0, 0]

    def reset_game(self):
        self.scores = [0, 0]
        self.start_new_round()

    def draw(self, player_idx, source):
        if self.winner is not None:
            return
        if source == "deck" and self.deck:
            self.hands[player_idx].append(self.deck.pop())
        elif source == "discard" and self.discard_pile:
            self.hands[player_idx].append(self.discard_pile.pop())

    def discard(self, player_idx, card):
        if self.winner is not None:
            return
        if card in self.hands[player_idx]:
            self.hands[player_idx].remove(card)
            self.discard_pile.append(card)
            if self.check_gin(player_idx):
                self.end_round(player_idx)
            else:
                self.turn = 1 - player_idx

    # ------------------------
    # Deadwood & melds
    # ------------------------
    def calculate_deadwood(self, player_idx):
        hand = self.hands[player_idx][:]
        used = self.get_melds(player_idx)
        self.deadwood[player_idx] = len([c for c in hand if c not in used])
        return self.deadwood[player_idx]

    def get_melds(self, player_idx):
        hand = self.hands[player_idx][:]
        used = set()

        # Sets
        ranks = {}
        for card in hand:
            r = card[:-1]
            ranks.setdefault(r, []).append(card)
        for group in ranks.values():
            if len(group) >= 3:
                used.update(group)

        # Runs
        suits = {s: [] for s in SUITS}
        for card in hand:
            r = card[:-1]
            s = card[-1]
            suits[s].append(card)
        for suit_cards in suits.values():
            sorted_cards = sorted(suit_cards, key=lambda c: RANK_VALUES[c[:-1]])
            run = []
            last_val = None
            for c in sorted_cards:
                val = RANK_VALUES[c[:-1]]
                if last_val is None or val == last_val + 1:
                    run.append(c)
                else:
                    if len(run) >= 3:
                        used.update(run)
                    run = [c]
                last_val = val
            if len(run) >= 3:
                used.update(run)
        return used

    def can_knock(self, player_idx):
        return self.calculate_deadwood(player_idx) <= 10

    def check_gin(self, player_idx):
        return self.calculate_deadwood(player_idx) == 0

    # ------------------------
    # Round scoring
    # ------------------------
    def end_round(self, player_idx):
        opponent = 1 - player_idx
        self.calculate_deadwood(player_idx)
        self.calculate_deadwood(opponent)

        if self.check_gin(player_idx):
            self.scores[player_idx] += 25 + self.deadwood[opponent]
        elif self.can_knock(player_idx):
            if self.deadwood[player_idx] < self.deadwood[opponent]:
                self.scores[player_idx] += self.deadwood[opponent] - self.deadwood[player_idx]
            else:
                self.scores[opponent] += 25 + self.deadwood[player_idx]

        self.winner = player_idx

    def knock(self, player_idx):
        if self.can_knock(player_idx):
            self.end_round(player_idx)

    # ------------------------
    # Sort hand for display
    # ------------------------
    def sorted_hand(self, player_idx):
        hand = self.hands[player_idx][:]
        melds = self.get_melds(player_idx)
        meld_cards = [c for c in hand if c in melds]
        deadwood_cards = [c for c in hand if c not in melds]

        def sort_key(c):
            return (RANK_VALUES[c[:-1]], SUITS.index(c[-1]))

        return sorted(meld_cards, key=sort_key) + sorted(deadwood_cards, key=sort_key)

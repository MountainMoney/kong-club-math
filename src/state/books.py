"Handles independent simulation events and details."

from copy import deepcopy


class Book:
    "Stores simulation information."

    def __init__(self, book_id: int):
        "Initialize simulation book"
        self.id = book_id
        self.payout_multiplier = 0.0
        self.events = []
        self.criteria = ""
        self.basegame_wins = 0.0
        self.freegame_wins = 0.0

    def add_event(self, event: dict):
        "Append event to book."
        self.events.append(deepcopy(event))

    def to_json(self):
        "Return JSON-ready object."
        json_book = {
            "id": self.id,
            "payoutMultiplier": self.payout_multiplier,
            "events": self.events,
            "criteria": self.criteria,
            "baseGameWins": self.basegame_wins,
            "freeGameWins": self.freegame_wins,
        }
        return json_book

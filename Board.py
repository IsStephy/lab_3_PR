import asyncio
from collections import deque
from typing import List, Optional

try:
    from .Card import Card  
except Exception:
    from Card import Card  


class Board:

    def __init__(self) -> None:
        self._player_state: dict[str, dict] = {}
        self._nr_cols: int = 0
        self._nr_rows: int = 0
        self._cards: list[list['Card']] = []
        self._change_event = asyncio.Event()
        self._board_lock = asyncio.Lock()
        self._waiting_players_queue: dict[tuple[int, int], deque[str]] = {}

    def checkRep(self) -> None:
        assert self._nr_rows >= 0, "Number of rows must be non-negative"
        assert self._nr_cols >= 0, "Number of columns must be non-negative"
        assert isinstance(self._cards, list), "_cards must be a list"

        if self._nr_rows == 0 or self._nr_cols == 0:
            assert len(self._cards) == 0, "Empty board must have empty cards list"
            return

        assert len(self._cards) == self._nr_rows, "Row dimension mismatch"

        controlled_on_board = set()
        for r in range(self._nr_rows):
            row = self._cards[r]
            assert isinstance(row, list), "Each row in _cards must be a list"
            assert len(row) == self._nr_cols, f"Column dimension mismatch in row {r}"

            for c in range(self._nr_cols):
                card = self.get_card(r, c)
                assert isinstance(card, Card), f"Item at ({r},{c}) is not a Card"

                card.checkRep()

                if card.controller is not None:
                    controlled_on_board.add(((r, c), card.controller))

        controlled_in_state = set()
        for p_id, state in self._player_state.items():
            assert isinstance(state, dict), f"Player state for {p_id} is not a dict"

            cards_this_round = state.get("cards_this_round")
            assert cards_this_round is not None, f"Player {p_id} missing 'cards_this_round'"
            assert isinstance(cards_this_round, list), f"'cards_this_round' for {p_id} must be a list"

            assert len(cards_this_round) <= 2, f"Player {p_id} controls {len(cards_this_round)} cards"

            for (r, c) in cards_this_round:
                assert 0 <= r < self._nr_rows, f"Invalid row {r} in player {p_id} state"
                assert 0 <= c < self._nr_cols, f"Invalid col {c} in player {p_id} state"
                controlled_in_state.add(((r, c), p_id))

        assert controlled_on_board == controlled_in_state, \
            f"Mismatch between board controllers and player state.\n" \
            f"Board: {controlled_on_board}\nState: {controlled_in_state}"

        for (r, c), queue in self._waiting_players_queue.items():
            assert 0 <= r < self._nr_rows, f"Invalid row {r} in queue key"
            assert 0 <= c < self._nr_cols, f"Invalid col {c} in queue key"
            assert isinstance(queue, deque), f"Queue at ({r},{c}) is not a deque"

            assert len(queue) == len(set(queue)), f"Duplicate player in queue at ({r},{c})"

            if len(queue) > 0:
                card = self.get_card(r, c)
                assert card.controller is not None, \
                    f"Queue exists for uncontrolled card at ({r},{c})"
                for p_id in queue:
                    assert card.controller != p_id, \
                        f"Player {p_id} in queue for their own card at ({r},{c})"

    @property
    def nr_cols(self) -> int:
        return self._nr_cols

    @nr_cols.setter
    def nr_cols(self, value: int):
        self._nr_cols = value

    @property
    def nr_rows(self) -> int:
        return self._nr_rows

    @nr_rows.setter
    def nr_rows(self, value: int):
        self._nr_rows = value

    @property
    def cards(self) -> List[List['Card']]:
        return self._cards

    @cards.setter
    def cards(self, value: List[List['Card']]):
        self._cards = value

    @property
    def player_state(self) -> dict:
        return self._player_state

    @property
    def waiting_players_queue(self) -> dict:
        return self._waiting_players_queue

    @property
    def change_event(self) -> asyncio.Event:
        return self._change_event

    @property
    def board_lock(self):
        return self._board_lock

    def get_card(self, row: int, col: int) -> Card:
        return self.cards[row][col]

    def __str__(self) -> str:
        board_rows = []
        for r in range(self.nr_rows):
            row_string = " ".join(str(self.cards[r][c]) for c in range(self.nr_cols))
            board_rows.append(row_string)
        return "\n".join(board_rows)

    def initialize_player_state(self, player_id: str) -> None:
        if player_id not in self.player_state:
            self.player_state[player_id] = {
                "cards_this_round": [],
                "cards_last_turn": [],
                "last_turn_matched": False
            }

    def initialize_queue_for_card(self, row, column) -> None:
        if (row, column) not in self.waiting_players_queue:
            self.waiting_players_queue[(row, column)] = deque()

    @staticmethod
    async def parse_from_file(filename: str) -> "Board":
        board = Board()
        try:
            contents = await asyncio.to_thread(Board._read_file_sync, filename)
            lines = contents.strip().splitlines()

            board_size = lines[0].strip()
            size_parts = board_size.split("x")
            if len(size_parts) != 2:
                raise ValueError("Invalid board size format, expected RxC like '3x3'")

            board.nr_rows = int(size_parts[0])
            board.nr_cols = int(size_parts[1])

            card_values = [line.strip() for line in lines[1:]]
            expected_nr_cards = board.nr_rows * board.nr_cols
            if len(card_values) != expected_nr_cards:
                raise ValueError(f"Invalid number of cards: expected {expected_nr_cards}, "
                                 f"got {len(card_values)}")

            board.cards = []
            i = 0
            for r in range(board.nr_rows):
                row_cards = []
                for c in range(board.nr_cols):
                    card_value = card_values[i]
                    card = Card(string_value=card_value)
                    row_cards.append(card)
                    i += 1
                board.cards.append(row_cards)

            return board

        except Exception as e:
            raise Exception(f"Error reading file '{filename}': {e}")

    @staticmethod
    def _read_file_sync(filename: str) -> str:
        with open(filename, "r", encoding="utf-8") as f:
            return f.read()
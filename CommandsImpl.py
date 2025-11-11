from typing import Optional, Callable, Awaitable
try:
    from .Board import Board
except Exception:  
    from Board import Board


class Commands:
    def __init__(self, board: Board):
        self.board = board

    async def clean_cards_last_round(self, player_id: str) -> None:
        self.board.initialize_player_state(player_id)

        state = self.board.player_state[player_id]
        cards_to_clean = state["cards_last_turn"]
        matched_status = state["last_turn_matched"]

        if not cards_to_clean:
            return

        if matched_status:
            print(f"[{player_id}] Cleaning up matched pair: {cards_to_clean}")
            for row, column in cards_to_clean:
                card = self.board.get_card(row, column)

                if card.controller == player_id:
                    card.removed = True
                    card.face_up = False
                    card.controller = None
                    self.board.initialize_queue_for_card(row, column)
                    queue = self.board.waiting_players_queue[(row, column)]

                    if queue:
                        print(f"Clearing queue for removed card ({row},{column}).")
                        queue.clear()

        else:
            print(f"[{player_id}] Cleaning up mismatched cards: {cards_to_clean}")
            for row, column in cards_to_clean:
                card = self.board.get_card(row, column)
                # Don't clean if card is currently controlled by anyone or is matched/removed
                if not card.removed and not card.matched and card.controller is None and card.face_up:
                    card.face_up = False
                    card.face_down = True


    async def release_control_and_update_queue(self, row: int, col: int) -> None:
        card = self.board.get_card(row, col)
        self.board.initialize_queue_for_card(row, col)
        queue = self.board.waiting_players_queue[(row, col)]

        if card.matched:
            card.controller = None
            if queue and len(queue) > 0:
                queue.clear()
                print(f"Cleared queue for matched card ({row},{col}).")
            return

        if queue and len(queue) > 0:
            next_player_id = queue.popleft()
            self.board.initialize_player_state(next_player_id)

            next_player_state = self.board.player_state[next_player_id]
            next_player_state["cards_this_round"].clear()

            card.controller = next_player_id
            next_player_state["cards_this_round"].append((row, col))

            print(f"[{next_player_id}] gained control of ({row},{col}) from queue.")
            self.notify_watchers()
        else:
            card.controller = None

    async def flip(self, player_id: str, row: int, col: int) -> Optional[str]:
        async with self.board.board_lock:
            self.board.initialize_player_state(player_id)
            self.board.initialize_queue_for_card(row, col)

            for (r, c), queue in self.board.waiting_players_queue.items():
                if player_id in queue:
                    raise Exception(
                        f"already waiting to flip a card"
                    )

            state = self.board.player_state[player_id]
            current_cards = state["cards_this_round"]
            card = self.board.get_card(row, col)

            queue_players = self.board.waiting_players_queue[(row, col)]

            if len(current_cards) == 0:
                await self.clean_cards_last_round(player_id)

                if card.removed:
                    raise Exception("Card is not on the board.")

                if card.matched:
                    raise Exception("Card is already matched and will be removed.")

                if card.controller is not None:
                    if player_id not in queue_players:
                        queue_players.append(player_id)
                        print(f"[{player_id}] was added to the queue for ({row},{col})")
                        self.notify_watchers()
                        raise Exception("Card is controlled. You are now in the queue.")
                    else:
                        raise Exception("You are already in the queue for this card.")

                if card.face_down:
                    card.face_up = True
                    card.face_down = False
                    print(f"[{player_id}] Flipped first card.")
                elif card.face_up and card.controller is None:
                    print(f"[{player_id}] Took control of face-up card.")

                for other_player_id, other_state in self.board.player_state.items():
                    if player_id != other_player_id:
                        if (row, col) in other_state["cards_last_turn"]:
                            print(f"[{player_id}] Taking control of ({row},{col}) from {other_player_id}, clearing their last turn")
                            other_state["cards_last_turn"].clear()
                            break
                card.controller = player_id
                current_cards.append((row, col))
                self.notify_watchers()
                return "First card selected."

            elif len(current_cards) == 1:
                await self.clean_cards_last_round(player_id)
                
                first_card_position = current_cards[0]
                first_card = self.board.get_card(first_card_position[0], first_card_position[1])

                if first_card_position == (row, col):
                    print(f"[{player_id}] Failed by selecting same card twice.")
                    await self.release_control_and_update_queue(first_card_position[0], first_card_position[1])
                    state["cards_last_turn"] = [first_card_position]
                    state["last_turn_matched"] = False
                    current_cards.clear()

                    raise Exception("Cannot select the same card twice.")

                first_card = self.board.get_card(first_card_position[0], first_card_position[1])

                if card.removed:
                    await self.release_control_and_update_queue(first_card_position[0], first_card_position[1])
                    state["cards_last_turn"] = [first_card_position]
                    state["last_turn_matched"] = False
                    current_cards.clear()
                    self.notify_watchers()
                    raise Exception("Second card is not on the board. Lost control of first card.")

                if card.matched:
                    await self.release_control_and_update_queue(first_card_position[0], first_card_position[1])
                    state["cards_last_turn"] = [first_card_position]
                    state["last_turn_matched"] = False
                    current_cards.clear()
                    self.notify_watchers()
                    raise Exception("Second card is already matched. Lost control of first card.")

                if card.controller is not None:
                    await self.release_control_and_update_queue(first_card_position[0], first_card_position[1])
                    state["cards_last_turn"] = [first_card_position]
                    state["last_turn_matched"] = False
                    current_cards.clear()
                    self.notify_watchers()
                    raise Exception("Second card is controlled. Lost control of first card.")

                if card.face_down:
                    card.face_up = True
                    card.face_down = False
                    print(f"[{player_id}] Flipped second card.")

                state["cards_last_turn"] = [first_card_position, (row, col)]

                if first_card.string_value == card.string_value:
                    print(f"[{player_id}] Match found!")
                    card.controller = player_id
                    state["last_turn_matched"] = True
                    first_card.matched = True
                    card.matched = True
                    current_cards.clear()
                    self.notify_watchers()
                    return "A match was found! User controls both cards."
                else:
                    print(f"[{player_id}] No match.")
                    await self.release_control_and_update_queue(first_card_position[0], first_card_position[1])
                    state["last_turn_matched"] = False
                    current_cards.clear()
                    self.notify_watchers()
                    return "No match found. Cards remain face up. Player no longer has control of first card."

            else:
                raise Exception("Invalid state: player has 2 cards in hand.")

    async def look(self, player_id: str) -> str:
        self.board.initialize_player_state(player_id)

        header = f"{self.board.nr_rows}x{self.board.nr_cols}"
        result = [header]

        for row in range(self.board.nr_rows):
            row_string = []
            for column in range(self.board.nr_cols):
                card = self.board.get_card(row, column)

                if card.removed:
                    status = "none"
                    text = "_"
                elif card.face_down:
                    status = "down"
                    text = "?"
                elif card.face_up:
                    if card.controller == player_id:
                        status = "my"
                    else:
                        status = "up"
                    text = card.string_value
                else:
                    status = "none"
                    text = "_"

                row_string.append(f"{status}:{text}")
            result.append(" ".join(row_string))

        return "\n".join(result)



    async def reset_board(self) -> None:
        print("Resetting the board...")
        async with self.board.board_lock:
            # 1. Reset all cards on the board
            for r in range(self.board.nr_rows):
                for c in range(self.board.nr_cols):
                    card = self.board.get_card(r, c)
                    card.face_down = True
                    card.face_up = False
                    card.removed = False
                    card.controller = None
                    card.matched = False

            self.board.player_state.clear()

            self.board.waiting_players_queue.clear()

            print("Board has been reset.")

        self.notify_watchers()

    async def replace_card_value(self, old_value: str, new_value: str) -> None:
        if not old_value or not new_value:
            raise ValueError("Both 'old' and 'new' values are required.")

        if old_value == new_value:
            raise ValueError("Old and new cards cannot be the same.")

        async with self.board.board_lock:
            print(f"Attempting to replace '{old_value}' with '{new_value}'")
            unique_values = set()
            for row in range(self.board.nr_rows):
                for column in range(self.board.nr_cols):
                    if not self.board.cards[row][column].removed:
                        unique_values.add(self.board.cards[row][column].string_value)

            if old_value not in unique_values:
                raise ValueError(f"Card value '{old_value}' not found on the board.")

            if new_value in unique_values:
                raise ValueError(f"Card value '{new_value}' is already on the board. Cards must be unique.")

            replaced_count = 0
            for row in range(self.board.nr_rows):
                for column in range(self.board.nr_cols):
                    card = self.board.get_card(row, column)
                    if not card.removed and card.string_value == old_value:
                        card.string_value = new_value
                        replaced_count += 1

            print(f"Replaced {replaced_count} instances of '{old_value}'.")
            print("Replacement complete.")

        self.notify_watchers()

    def notify_watchers(self) -> None:
        self.board.change_event.set()

    async def wait_for_change(self) -> None:
        await self.board.change_event.wait()
        self.board.change_event.clear()
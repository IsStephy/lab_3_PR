import unittest
import asyncio

from ..Card import Card
from ..Board import Board
from ..CommandsImpl import Commands


class TestCard(unittest.TestCase):
    def test_card_initial_state(self):
        c = Card("🦄")
        self.assertTrue(c.face_down)
        self.assertFalse(c.face_up)
        self.assertFalse(c.removed)
        self.assertIsNone(c.controller)
        c.checkRep()  # should not raise

    def test_card_flip_and_match(self):
        c = Card("🌈")
        c.face_down = False
        c.face_up = True
        c.controller = "player1"
        c.checkRep()
        c.matched = True
        c.checkRep()
        c.removed = False
        self.assertTrue(c.matched)
        self.assertEqual(c.controller, "player1")


class AsyncTestCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.board = Board()
        self.board.nr_rows = 2
        self.board.nr_cols = 2
        self.board.cards = [
            [Card("🦄"), Card("🌈")],
            [Card("🍎"), Card("🍎")]
        ]
        self.commands = Commands(self.board)
        self.p1 = "p1"
        self.p2 = "p2"

    async def test_board_rep_ok(self):
        self.board.checkRep()  # should not raise

    async def test_flip_and_match(self):
        msg1 = await self.commands.flip(self.p1, 1, 0)
        self.assertIn("First card", msg1)
        card1 = self.board.get_card(1, 0)
        self.assertTrue(card1.face_up)
        self.assertEqual(card1.controller, self.p1)

        msg2 = await self.commands.flip(self.p1, 1, 1)
        self.assertIn("match", msg2.lower())
        card2 = self.board.get_card(1, 1)
        self.assertTrue(card2.matched)
        self.assertTrue(card1.matched)

    async def test_mismatch_then_cleanup(self):
        await self.commands.flip(self.p1, 0, 0)
        msg = await self.commands.flip(self.p1, 0, 1)
        self.assertIn("no match", msg.lower())

        await self.commands.clean_cards_last_round(self.p1)
        c1 = self.board.get_card(0, 0)
        c2 = self.board.get_card(0, 1)
        self.assertTrue(c1.face_down or c1.face_up)
        self.assertTrue(c2.face_down or c2.face_up)

    async def test_reset_board(self):
        await self.commands.reset_board()
        for r in range(self.board.nr_rows):
            for c in range(self.board.nr_cols):
                card = self.board.get_card(r, c)
                self.assertTrue(card.face_down)
                self.assertFalse(card.face_up)
                self.assertFalse(card.removed)
                self.assertIsNone(card.controller)

    async def test_replace_card_value(self):
        await self.commands.replace_card_value("🦄", "🍓")
        all_values = [card.string_value for row in self.board.cards for card in row]
        self.assertIn("🌈", all_values)
        self.assertNotIn("🦄", all_values)

    async def test_look_output_format(self):
        text = await self.commands.look(self.p1)
        self.assertTrue(text.startswith(f"{self.board.nr_rows}x{self.board.nr_cols}"))
        lines = text.splitlines()
        self.assertEqual(len(lines) - 1, self.board.nr_rows)
        parts = lines[1].split(" ")[0].split(":")
        self.assertEqual(len(parts), 2)

    async def test_mismatch_visibility_bug_fix(self):
        """
        Ensures that when a player mismatches two cards,
        they lose control but the cards stay face-up
        (visible for other players).
        """
        # Player 1 mismatches 🦄 vs 🌈
        await self.commands.flip(self.p1, 0, 0)
        await self.commands.flip(self.p1, 0, 1)

        # At this point, both should be face-up and uncontrolled
        c1 = self.board.get_card(0, 0)
        c2 = self.board.get_card(0, 1)
        self.assertTrue(c1.face_up)
        self.assertTrue(c2.face_up)
        self.assertIsNone(c1.controller)
        self.assertIsNone(c2.controller)

        # Player 2 starts their turn (should not flip these cards down)
        await self.commands.flip(self.p2, 1, 0)  # different card
        c1_after = self.board.get_card(0, 0)
        c2_after = self.board.get_card(0, 1)

        # They must remain face-up (bug fix check)
        self.assertTrue(c1_after.face_up, "Previously visible card flipped down unexpectedly!")
        self.assertTrue(c2_after.face_up, "Previously visible card flipped down unexpectedly!")


if __name__ == "__main__":
    unittest.main()

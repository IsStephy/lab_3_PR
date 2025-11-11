import asyncio
import random
import aiohttp

SERVER_URL = "http://localhost:8000"
NUM_PLAYERS = 4
MOVES_PER_PLAYER = 100
MIN_DELAY = 0.0001   # 0.1 ms
MAX_DELAY = 0.002    # 2 ms


async def random_move(session, player_id):
    # Get current board to know dimensions
    async with session.get(f"{SERVER_URL}/look/{player_id}") as resp:
        text = await resp.text()
        lines = text.strip().splitlines()
        dims = lines[0].split("x")
        rows, cols = int(dims[0]), int(dims[1])

    # Pick a random cell
    r = random.randint(0, rows - 1)
    c = random.randint(0, cols - 1)

    # Try to flip
    async with session.get(f"{SERVER_URL}/flip/{player_id}/{r},{c}") as resp:
        text = await resp.text()
        if resp.status != 200:
            print(f"[{player_id}] move ({r},{c}) failed: {text.strip()}")
        else:
            print(f"[{player_id}] flipped ({r},{c}) OK")


async def player_task(player_id):
    async with aiohttp.ClientSession() as session:
        for i in range(MOVES_PER_PLAYER):
            try:
                await random_move(session, player_id)
            except Exception as e:
                print(f"[{player_id}] error: {e}")
            await asyncio.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
    print(f"[{player_id}] finished all moves.")


async def main():
    players = [f"sim_player_{i}" for i in range(NUM_PLAYERS)]
    tasks = [asyncio.create_task(player_task(pid)) for pid in players]
    await asyncio.gather(*tasks)
    print("Simulation complete — all players finished.")


if __name__ == "__main__":
    asyncio.run(main())
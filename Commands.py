
try:
    from .CommandsImpl import Commands
except Exception:
    from CommandsImpl import Commands


async def flip(commands: Commands, player_id: str, row: int, col: int) -> str:
    return await commands.flip(player_id, row, col)


async def look(commands: Commands, player_id: str) -> str:
    return await commands.look(player_id)


async def watch(commands: Commands, player_id: str) -> str:
    await commands.wait_for_change()
    return await commands.look(player_id)


async def reset_board(commands: Commands,) -> None:
    await commands.reset_board()


async def apply_replace_command(commands: Commands, old_value: str, new_value: str) -> None:
    await commands.replace_card_value(old_value, new_value)
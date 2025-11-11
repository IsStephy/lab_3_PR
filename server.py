import os
import sys
import asyncio
from quart import Quart, Response, send_from_directory, request
from http import HTTPStatus

from Board import Board
from CommandsImpl import Commands
from Commands import (
    flip, look, watch,
    map as map_command,  # Rename to avoid conflict with built-in map()
    reset_board
)


class WebServer:
    def __init__(self, port: int, commands: Commands):
        self.port = port
        self.commands = commands

        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        PUBLIC_DIR = os.path.join(BASE_DIR, "public")
        self.app = Quart(__name__, static_folder="public", static_url_path="")

        @self.app.after_request
        async def add_cors_headers(response):
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type"
            return response

        @self.app.get("/look/<player_id>")
        async def look_route(player_id):
            board_state = await look(self.commands, player_id)
            return Response(board_state, status=HTTPStatus.OK, mimetype="text/plain")

        @self.app.get("/flip/<player_id>/<location>")
        async def flip_route(player_id, location):
            try:
                row, column = list(builtins_map(int, location.split(",")))  # Use built-in map explicitly
                play_message = await flip(self.commands, player_id, row, column)
                board_state = await look(self.commands, player_id)
                print(f"[{player_id}] Move result: {play_message}")
                return Response(board_state, status=HTTPStatus.OK, mimetype="text/plain")
            except Exception as e:
                return Response(
                    f"Move failed: {e}",
                    status=HTTPStatus.CONFLICT,
                    mimetype="text/plain",
                )

        @self.app.post("/replace")
        async def replace_route():
            try:
                data = await request.get_json()
                if not data:
                    raise ValueError("Missing JSON request body")

                old_value = data.get("old")
                new_value = data.get("new")

                if not old_value or not new_value:
                    raise ValueError("Request must include 'old' and 'new' keys.")

                await map_command(self.commands, old_value, new_value)

                return Response("Replacement successful", status=HTTPStatus.OK, mimetype="text/plain")

            except (ValueError, Exception) as e:
                print(f"Error during /replace: {e}")
                return Response(
                    f"Failed to replace: {e}",
                    status=HTTPStatus.BAD_REQUEST,
                    mimetype="text/plain",
                )
            
        @self.app.get("/replace/<player_id>/<old_value>/<new_value>")
        async def replace_get_route(player_id, old_value, new_value):
            try:
                await map_command(self.commands, old_value, new_value)
                board_state = await look(self.commands, player_id)
                return Response(board_state, status=HTTPStatus.OK, mimetype="text/plain")
            except (ValueError, Exception) as e:
                print(f"Error during GET /replace: {e}")
                return Response(
                    f"Failed to replace: {e}",
                    status=HTTPStatus.BAD_REQUEST,
                    mimetype="text/plain",
                )


        @self.app.get("/watch/<player_id>")
        async def watch_route(player_id):
            # Use self.commands
            board_state = await watch(self.commands, player_id)
            return Response(board_state, status=HTTPStatus.OK, mimetype="text/plain")

        @self.app.route("/")
        async def serve_index():
            return await send_from_directory(PUBLIC_DIR, "index.html")

        @self.app.route("/reset", methods=["POST"])
        async def handle_reset():
            try:
                await reset_board(self.commands)
                return "Board reset successfully.", HTTPStatus.OK
            except Exception as e:
                print(f"Error during reset: {e}")
                return str(e), HTTPStatus.INTERNAL_SERVER_ERROR

import builtins
builtins_map = builtins.map

def main():
    if len(sys.argv) < 3:
        print("Usage: python server.py PORT FILENAME")
        sys.exit(1)

    port = int(sys.argv[1])
    filename = sys.argv[2]

    async def run_server():
        board = await Board.parse_from_file(filename)
        commands = Commands(board)
        server = WebServer(port, commands)

        from hypercorn.config import Config
        from hypercorn.asyncio import serve

        config = Config()
        config.bind = [f"0.0.0.0:{port}"]
        config.use_reloader = False

        print(f"Hypercorn server (with Quart) listening at http://localhost:{port}")

        await serve(server.app, config)

    asyncio.run(run_server())


if __name__ == "__main__":
    main()
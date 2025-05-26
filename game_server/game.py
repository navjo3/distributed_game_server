import asyncio
import json
from websockets.server import WebSocketServerProtocol, serve  # Updated import path
from datetime import datetime, UTC
import os
# import weakref # REMOVE THIS

# Server configuration
GAME_SERVER_PORT = int(os.environ.get("GAME_PORT", 9001))

# Global state for game.py
# players: websocket -> player_id (username)
# rooms: room_id (match_id) -> { 'players': set of player_ids (usernames), 'game_state': {...} }
# player_room_map: player_id (username) -> room_id (match_id)

# --- STATE MANAGEMENT (More robust) ---
# These will store state PER GAME INSTANCE (i.e., per room_id derived from path)
# For a single game.py process handling multiple rooms via path:
game_sessions = {} #  match_id: { "players": {player_id: websocket}, "state": {...game specific state...} }

def get_match_id_from_path(path: str):
    # Path will be like "/game/MATCH_ID"
    parts = path.strip("/").split("/")
    if len(parts) == 2 and parts[0] == "game":
        return parts[1]
    return None

async def handle_player(websocket: WebSocketServerProtocol, path: str):
    match_id = get_match_id_from_path(path)
    if not match_id:
        print(f"[{timestamp()}] Invalid path: {path}. Closing connection.")
        await websocket.close(code=1003, reason="Invalid path") # 1003: cannot accept data
        return

    player_id = None # Will be the username

    try:
        # Initialize game session if it's the first player for this match_id
        if match_id not in game_sessions:
            game_sessions[match_id] = {
                "players": {}, # player_id (username): websocket
                "state": initialize_game_state() # Implement this function
            }
            print(f"[{timestamp()}] Initialized game session for match_id: {match_id}")

        session = game_sessions[match_id]

        async for message_str in websocket:
            try:
                data = json.loads(message_str)
            except json.JSONDecodeError:
                print(f"[{timestamp()}] Invalid JSON from {player_id or websocket.remote_address} in {match_id}: {message_str}")
                await websocket.send(json.dumps({"type": "error", "message": "Invalid JSON format"}))
                continue

            action_type = data.get("type") # Client sends "type"

            if action_type == "join":
                # Client sends: {"type": "join", "username": "user123"}
                username = data.get("username")
                if not username:
                    await websocket.send(json.dumps({"type": "error", "message": "Username missing in join message."}))
                    continue
                
                if player_id and player_id != username: # Should not happen if client is well-behaved
                     await websocket.send(json.dumps({"type": "error", "message": "Username mismatch."}))
                     continue
                
                player_id = username # Set player_id for this connection

                # Check if player already in session (e.g. reconnect with same username but different websocket)
                if player_id in session["players"] and session["players"][player_id] != websocket:
                    print(f"[{timestamp()}] Player {player_id} rejoining/already joined in {match_id}. Closing old connection if any.")
                    old_ws = session["players"].get(player_id)
                    if old_ws and old_ws != websocket:
                        await old_ws.close(reason="New connection for player") #
                
                session["players"][player_id] = websocket
                # Add player to game state if not already there
                if player_id not in session["state"]["players"]:
                     session["state"]["players"][player_id] = {"score": 0, "position": (0,0)} # Example

                print(f"[{timestamp()}] Player {player_id} joined match {match_id}")

                # Notify others in the room (optional, or rely on next game_state broadcast)
                await broadcast_to_session(match_id, {
                    "type": "player_event", # Generic event type
                    "event": "player_joined",
                    "player_id": player_id
                }, exclude_player_id=player_id)

                # Send initial game state or ack
                await websocket.send(json.dumps({"type": "join_ack", "status": "success", "player_id": player_id, "match_id": match_id}))
                await websocket.send(json.dumps({"type": "game_state", "state": session["state"]}))


            elif action_type == "move":
                # Client sends: {"type": "move", "direction": "up"}
                if not player_id: # Player must have joined first
                    await websocket.send(json.dumps({"type": "error", "message": "Must join before moving."}))
                    continue

                direction = data.get("direction")
                if not direction:
                    await websocket.send(json.dumps({"type": "error", "message": "Direction missing in move."}))
                    continue

                print(f"[{timestamp()}] Player {player_id} in match {match_id} moved: {direction}")
                
                # --- ACTUAL GAME LOGIC HERE ---
                # update_game_state_on_move(session["state"], player_id, direction)
                # This function would modify session["state"] (e.g. player position, score)
                # For example:
                # new_pos = calculate_new_pos(session["state"]["players"][player_id]["position"], direction)
                # session["state"]["players"][player_id]["position"] = new_pos
                # if new_pos == gem_location: session["state"]["players"][player_id]["score"] +=1 etc.
                # session["state"]["time_remaining"] -= 0.1 # if moves tick time
                
                # For now, just echo back, but you need real logic
                # For simplicity, let's assume some game state update
                session["state"]["last_move_by"] = player_id 
                session["state"]["last_direction"] = direction

                # Broadcast new game state to all in the same session
                await broadcast_to_session(match_id, {"type": "game_state", "state": session["state"]})

            # No explicit "leave" from client, handled by disconnect.
            # If client *did* send a "leave", you'd call handle_disconnect here.

            else:
                print(f"[{timestamp()}] Unknown action type from {player_id} in {match_id}: {action_type}")
                await websocket.send(json.dumps({"type": "error", "message": f"Unknown action type: {action_type}"}))


    except websockets.exceptions.ConnectionClosedOK:
        print(f"[{timestamp()}] Player {player_id or websocket.remote_address} disconnected gracefully from {match_id}.")
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"[{timestamp()}] Player {player_id or websocket.remote_address} connection closed with error from {match_id}: {e}")
    except Exception as e:
        print(f"[{timestamp()}] Error in handler for {player_id or websocket.remote_address} in {match_id}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if player_id and match_id and match_id in game_sessions:
            await handle_disconnect(player_id, match_id, websocket)

async def handle_disconnect(player_id, match_id, websocket_that_disconnected):
    session = game_sessions.get(match_id)
    if not session:
        return

    # Only remove if the disconnected websocket is the one registered for this player_id
    if session["players"].get(player_id) == websocket_that_disconnected:
        print(f"[{timestamp()}] Player {player_id} disconnected from match {match_id}")
        session["players"].pop(player_id, None)
        
        # Also remove player from game state representation if necessary
        if "players" in session["state"] and player_id in session["state"]["players"]:
            session["state"]["players"].pop(player_id, None) # Example, adjust based on your state structure

        if not session["players"]:
            print(f"[{timestamp()}] Match {match_id} is empty. Cleaning up session.")
            del game_sessions[match_id]
        else:
            # Notify remaining players
            await broadcast_to_session(match_id, {
                "type": "player_event",
                "event": "player_left",
                "player_id": player_id
            })
            # Optionally send updated game state if player leaving affects it
            await broadcast_to_session(match_id, {"type": "game_state", "state": session["state"]})


async def broadcast_to_session(match_id, message_data, exclude_player_id=None):
    session = game_sessions.get(match_id)
    if not session:
        return

    try:
        message_json = json.dumps(message_data)
    except TypeError as e:
        print(f"[{timestamp()}] Error serializing message for broadcast in {match_id}: {e}")
        return

    disconnected_players_during_broadcast = [] # Store (pid, ws) tuples

    for pid, ws in list(session["players"].items()): # Iterate over a copy of items for safe modification
        if pid == exclude_player_id:
            continue
        try:
            await ws.send(message_json)
        except websockets.exceptions.ConnectionClosed:
            print(f"[{timestamp()}] Failed to send to {pid} in {match_id} (closed). Marking for disconnect.")
            disconnected_players_during_broadcast.append((pid, ws))
        except Exception as e:
            print(f"[{timestamp()}] Error sending to {pid} in {match_id}: {e}")
            # Depending on error, might also mark for disconnect

    for d_pid, d_ws in disconnected_players_during_broadcast:
        # Check if they haven't already been removed by another disconnect path
        if d_pid in session["players"] and session["players"][d_pid] == d_ws:
            await handle_disconnect(d_pid, match_id, d_ws)


def initialize_game_state():
    # TODO: Define your actual initial game state structure
    return {
        "grid": [[0]*10 for _ in range(10)], # Example 10x10 grid
        "players": {}, # player_id: {"score": 0, "position": (x,y)}
        "gems": [(1,1), (5,5)], # Example gem positions
        "time_remaining": 60,
        "game_over": False,
        "winner": None
    }

def timestamp():
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")

async def game_loop(): # If you need a periodic server-side loop for a game session
    while True:
        for match_id, session in list(game_sessions.items()): # Iterate copy
            if not session["state"]["game_over"]:
                session["state"]["time_remaining"] -= 1 # Example: decrement time
                if session["state"]["time_remaining"] <= 0:
                    session["state"]["game_over"] = True
                    # Determine winner logic here:
                    # session["state"]["winner"] = determine_winner(session["state"]["players"])
                    print(f"[{timestamp()}] Game over for match {match_id}")
                
                # Broadcast updated state due to game loop
                await broadcast_to_session(match_id, {"type": "game_state", "state": session["state"]})
            
            # If game over and no players, or some other cleanup condition
            if session["state"]["game_over"] and not session["players"]:
                 print(f"[{timestamp()}] Cleaning up finished and empty session {match_id}")
                 del game_sessions[match_id]

        await asyncio.sleep(1) # Game tick rate (1 second here)


async def main():
    print(f"[{timestamp()}] Game server started on ws://localhost:{GAME_SERVER_PORT}") # Use GAME_SERVER_PORT from client.py
    
    # If you have a game loop that affects all sessions (like time decrement)
    # asyncio.create_task(game_loop())

    # The port should match GAME_SERVER_PORT used by client and master
    # Client uses 9001 by default (from its GAME_SERVER_PORT variable)
    # Master.py GAME_PORT is 9001.
    # So game.py should listen on 9001.
    game_port_to_use = int(os.environ.get("GAME_PORT", 9001)) # Consistent port

    async with serve(handle_player, "0.0.0.0", game_port_to_use) as server:
        print(f"✅ Game server instance running on port {game_port_to_use}")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
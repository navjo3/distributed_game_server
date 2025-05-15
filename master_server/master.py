import asyncio
import websockets
import json
import threading
import uuid
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

MATCHMAKING_PORT = 8765
MATCHMAKING_WS_URL = f"ws://localhost:{MATCHMAKING_PORT}"
GAME_SERVER_WS_URL = "ws://localhost:9001/game/"
MAX_PLAYERS_PER_MATCH = 4

# Store rooms and their players
rooms = {}  # room_code -> {players: [(websocket, username)], host: username}
matchmaking_queue = []  # For players not specifying a room code
next_match_id = 1
active_connections = {}  # websocket -> (username, room_code)

@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"}), 200

@app.route("/join", methods=["POST"])
def join():
    try:
        if not request.is_json:
            return jsonify({"success": False, "message": "Content-Type must be application/json"}), 400

        data = request.get_json()
        if data is None:
            return jsonify({"success": False, "message": "Invalid JSON data"}), 400
            
        username = data.get("username")
        if not username:
            return jsonify({"success": False, "message": "Missing username"}), 400

        return jsonify({"success": True, "message": "Join successful"})
    except Exception as e:
        print(f"Error in /join endpoint: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/create_room", methods=["POST"])
def create_room():
    try:
        if not request.is_json:
            return jsonify({"success": False, "message": "Content-Type must be application/json"}), 400

        data = request.get_json()
        if data is None:
            return jsonify({"success": False, "message": "Invalid JSON data"}), 400
            
        username = data.get("username")
        if not username:
            return jsonify({"success": False, "message": "Missing username"}), 400
            
        # Generate a unique room code
        room_code = str(uuid.uuid4())[:6].upper()
        
        # Room will be properly initialized when the host connects via WebSocket
        
        return jsonify({
            "success": True, 
            "message": "Room created successfully", 
            "room_code": room_code
        })
    except Exception as e:
        print(f"Error in /create_room endpoint: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

async def matchmaking_handler(websocket):
    global next_match_id

    try:
        async for message in websocket:
            data = json.loads(message)
            
            if data.get("type") == "create_room":
                # Handle room creation
                username = data["username"]
                room_code = data["room_code"]
                
                if room_code in rooms:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "Room already exists"
                    }))
                    continue
                
                # Create the room with the user as host
                rooms[room_code] = {
                    "players": [(websocket, username)],
                    "host": username
                }
                
                # Store the connection info
                active_connections[websocket] = (username, room_code)
                
                # Send confirmation to the host
                await websocket.send(json.dumps({
                    "type": "room_created",
                    "room_code": room_code,
                    "host": username,
                    "players": [username],
                    "players_needed": MAX_PLAYERS_PER_MATCH - 1
                }))
                
            elif data.get("type") == "join_match":
                username = data["username"]
                room_code = data.get("room_code")
                
                if room_code:
                    # Join specific room
                    if room_code not in rooms:
                        await websocket.send(json.dumps({
                            "type": "error",
                            "message": "Room not found"
                        }))
                        continue
                    
                    # Check if room is already full
                    if len(rooms[room_code]["players"]) >= MAX_PLAYERS_PER_MATCH:
                        await websocket.send(json.dumps({
                            "type": "error",
                            "message": "Room is full"
                        }))
                        continue
                    
                    # Check if username is already taken in this room
                    room_usernames = [uname for _, uname in rooms[room_code]["players"]]
                    if username in room_usernames:
                        await websocket.send(json.dumps({
                            "type": "error",
                            "message": "Username already taken in this room"
                        }))
                        continue
                        
                    # Add player to room
                    rooms[room_code]["players"].append((websocket, username))
                    active_connections[websocket] = (username, room_code)
                    
                    players_in_room = len(rooms[room_code]["players"])
                    room_usernames = [uname for _, uname in rooms[room_code]["players"]]
                    
                    # Send room update to all players in the room
                    room_update = {
                        "type": "queue_update",
                        "players_needed": MAX_PLAYERS_PER_MATCH - players_in_room,
                        "room_code": room_code,
                        "players": room_usernames,
                        "host": rooms[room_code]["host"]
                    }
                    
                    for ws, _ in rooms[room_code]["players"]:
                        try:
                            await ws.send(json.dumps(room_update))
                        except:
                            pass

                    # Check if room is full
                    if players_in_room >= MAX_PLAYERS_PER_MATCH:
                        match_id = next_match_id
                        next_match_id += 1
                        players = rooms[room_code]["players"][:MAX_PLAYERS_PER_MATCH]
                        host = rooms[room_code]["host"]
                        
                        # Remove started match from rooms
                        del rooms[room_code]
                        
                        # Remove connections from active_connections
                        for ws, _ in players:
                            if ws in active_connections:
                                del active_connections[ws]
                        
                        await start_match(match_id, players, host)

                else:
                    # Join general matchmaking queue
                    print(f"{username} joined matchmaking queue.")
                    matchmaking_queue.append((websocket, username))
                    active_connections[websocket] = (username, None)

                    # Send queue update to all clients in queue
                    queue_update = {
                        "type": "queue_update",
                        "players_needed": MAX_PLAYERS_PER_MATCH - len(matchmaking_queue),
                        "players": [uname for _, uname in matchmaking_queue]
                    }
                    for ws, _ in matchmaking_queue:
                        try:
                            await ws.send(json.dumps(queue_update))
                        except:
                            pass

                    if len(matchmaking_queue) >= MAX_PLAYERS_PER_MATCH:
                        match_id = next_match_id
                        next_match_id += 1
                        players = matchmaking_queue[:MAX_PLAYERS_PER_MATCH]
                        host = players[0][1]  # First player becomes host
                        matchmaking_queue[:] = matchmaking_queue[MAX_PLAYERS_PER_MATCH:]
                        
                        # Remove connections from active_connections
                        for ws, _ in players:
                            if ws in active_connections:
                                del active_connections[ws]
                        
                        await start_match(match_id, players, host)
                        
            elif data.get("type") == "start_game" and data.get("room_code"):
                # Only host can start the game
                room_code = data["room_code"]
                username = data.get("username")
                
                if room_code not in rooms:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "Room not found"
                    }))
                    continue
                
                if rooms[room_code]["host"] != username:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "Only the host can start the game"
                    }))
                    continue
                
                # Check minimum players (at least 2)
                if len(rooms[room_code]["players"]) < 2:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "Need at least 2 players to start"
                    }))
                    continue
                
                # Start the game with current players
                match_id = next_match_id
                next_match_id += 1
                players = rooms[room_code]["players"]
                host = rooms[room_code]["host"]
                
                # Remove room
                del rooms[room_code]
                
                # Remove connections from active_connections
                for ws, _ in players:
                    if ws in active_connections:
                        del active_connections[ws]
                
                await start_match(match_id, players, host)

    except websockets.ConnectionClosed:
        print("WebSocket client disconnected.")
        await handle_disconnect(websocket)
    except Exception as e:
        print(f"Error in matchmaking handler: {str(e)}")
        await handle_disconnect(websocket)

async def handle_disconnect(websocket):
    # Check if the client was in active_connections
    if websocket in active_connections:
        username, room_code = active_connections[websocket]
        del active_connections[websocket]
        
        # Remove from rooms if in a specific room
        if room_code and room_code in rooms:
            for i, (ws, uname) in enumerate(rooms[room_code]["players"]):
                if ws == websocket:
                    rooms[room_code]["players"].pop(i)
                    
                    # If room is now empty, remove it
                    if not rooms[room_code]["players"]:
                        del rooms[room_code]
                        break
                    
                    # If the host left, assign a new host
                    if uname == rooms[room_code]["host"] and rooms[room_code]["players"]:
                        rooms[room_code]["host"] = rooms[room_code]["players"][0][1]
                    
                    # Update remaining players
                    room_usernames = [u for _, u in rooms[room_code]["players"]]
                    room_update = {
                        "type": "queue_update",
                        "players_needed": MAX_PLAYERS_PER_MATCH - len(rooms[room_code]["players"]),
                        "room_code": room_code,
                        "players": room_usernames,
                        "host": rooms[room_code]["host"],
                        "player_left": username
                    }
                    
                    for ws, _ in rooms[room_code]["players"]:
                        try:
                            await ws.send(json.dumps(room_update))
                        except:
                            pass
                    break

        # Remove from general queue
        for i, (ws, uname) in enumerate(matchmaking_queue):
            if ws == websocket:
                matchmaking_queue.pop(i)
                
                # Update remaining players in queue
                queue_update = {
                    "type": "queue_update",
                    "players_needed": MAX_PLAYERS_PER_MATCH - len(matchmaking_queue),
                    "players": [u for _, u in matchmaking_queue]
                }
                
                for ws, _ in matchmaking_queue:
                    try:
                        await ws.send(json.dumps(queue_update))
                    except:
                        pass
                break

async def start_match(match_id, players, host):
    player_names = [uname for _, uname in players]
    
    match_info = {
        "match_id": match_id,
        "game_server": f"{GAME_SERVER_WS_URL}{match_id}",
        "players": player_names,
        "host": host
    }

    for ws, _ in players:
        try:
            await ws.send(json.dumps({
                "type": "match_found",
                "match_id": match_id,
                "game_server": match_info["game_server"],
                "players": match_info["players"],
                "host": match_info["host"]
            }))
        except:
            pass

def start_websocket_server():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def start_server():
        async with websockets.serve(matchmaking_handler, "localhost", MATCHMAKING_PORT) as server:
            print(f"Matchmaking WebSocket running on {MATCHMAKING_WS_URL}")
            await asyncio.Future()  # run forever
    
    try:
        loop.run_until_complete(start_server())
    finally:
        loop.close()

def start_flask_server():
    print("Flask REST API running on http://localhost:5000")
    app.run(port=5000)

if __name__ == "__main__":
    threading.Thread(target=start_websocket_server, daemon=True).start()
    start_flask_server()
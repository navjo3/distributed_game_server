import asyncio
import websockets
import json
import random
import time
from typing import Dict, List, Tuple, Set
import uuid
import traceback

# Game constants
GRID_SIZE = 10
GEM_SPAWN_INTERVAL = 5  # seconds
GAME_DURATION = 60  # seconds
MAX_PLAYERS = 4
MIN_PLAYERS = 2

# Game state
class GameState:
    def __init__(self, match_id: str):
        self.match_id = match_id
        self.grid = [[0 for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]  # 0 = empty, 1 = gem
        self.players: Dict[str, Dict] = {}  # username -> {position: (x,y), score: int}
        self.start_time = None
        self.is_running = False
        self.last_gem_spawn = 0

    def add_player(self, username: str, position: Tuple[int, int]):
        self.players[username] = {
            "position": position,
            "score": 0
        }

    def remove_player(self, username: str):
        if username in self.players:
            del self.players[username]

    def move_player(self, username: str, direction: str) -> bool:
        if username not in self.players:
            return False

        x, y = self.players[username]["position"]
        new_x, new_y = x, y

        if direction == "up" and y > 0:
            new_y -= 1
        elif direction == "down" and y < GRID_SIZE - 1:
            new_y += 1
        elif direction == "left" and x > 0:
            new_x -= 1
        elif direction == "right" and x < GRID_SIZE - 1:
            new_x += 1
        else:
            return False

        # Check for gem collection
        if self.grid[new_y][new_x] == 1:
            self.players[username]["score"] += 1
            self.grid[new_y][new_x] = 0

        self.players[username]["position"] = (new_x, new_y)
        return True

    def spawn_gem(self):
        empty_cells = []
        for y in range(GRID_SIZE):
            for x in range(GRID_SIZE):
                if self.grid[y][x] == 0 and not any(p["position"] == (x, y) for p in self.players.values()):
                    empty_cells.append((x, y))
        
        if empty_cells:
            x, y = random.choice(empty_cells)
            self.grid[y][x] = 1

    def get_state(self) -> dict:
        return {
            "grid": self.grid,
            "players": self.players,
            "time_remaining": max(0, GAME_DURATION - (time.time() - self.start_time)) if self.start_time else GAME_DURATION,
            "game_over": self.is_game_over()
        }

    def is_game_over(self) -> bool:
        if not self.start_time:
            return False
        return time.time() - self.start_time >= GAME_DURATION

    def get_winner(self) -> str:
        if not self.is_game_over():
            return None
        return max(self.players.items(), key=lambda x: x[1]["score"])[0]

# Active games
active_games: Dict[str, GameState] = {}

# At the top of the file, add this import if not already present
import weakref

# Add this after the active_games declaration (around line 92)
connected_clients = {}

# Replace the broadcast_game_state function
async def broadcast_game_state(match_id: str):
    if match_id not in active_games:
        return

    game = active_games[match_id]
    state = game.get_state()
    print(f"Broadcasting game state for match {match_id}: {state}")
    
    # Check for game over
    if game.is_game_over():
        winner = game.get_winner()
        state["winner"] = winner
        state["game_over"] = True

    # Create the message once
    message = json.dumps({
        "type": "game_state",
        "state": state
    })
    
    # Get all connected websockets for this game
    if match_id in connected_clients:
        websockets_tasks = []
        for ws in connected_clients[match_id]:
            if not ws.closed:
                websockets_tasks.append(asyncio.create_task(ws.send(message)))
        
        if websockets_tasks:
            await asyncio.gather(*websockets_tasks, return_exceptions=True)

# At the top of the file with other imports
from websockets.asyncio.server import WebSocketServerProtocol, serve

# Keep this line where it appears in the file (around line 139)
WebSocketServerProtocol.instances = weakref.WeakSet()

# Modify the game_handler function to track connections
async def game_handler(websocket):
    """Handle game WebSocket connections"""
    try:
        # Get match_id from the path
        path = websocket.path
        match_id = path.split('/')[-1] if path else None
        print(f"New connection attempt for match {match_id}")
        
        if not match_id or match_id not in active_games:
            print(f"Game not found: {match_id}")
            await websocket.close(1000, "Game not found")
            return

        game = active_games[match_id]
        username = None

        # Add this websocket to connected clients for this match
        if match_id not in connected_clients:
            connected_clients[match_id] = set()
        connected_clients[match_id].add(websocket)

        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    print(f"Received message: {data}")
                    
                    if data["type"] == "join":
                        username = data["username"]
                        print(f"Player {username} joining match {match_id}")
                        
                        if len(game.players) >= MAX_PLAYERS:
                            print(f"Game {match_id} is full")
                            await websocket.send(json.dumps({
                                "type": "error",
                                "message": "Game is full"
                            }))
                            continue

                        # Assign starting position based on number of players
                        positions = [(0, 0), (GRID_SIZE-1, 0), (0, GRID_SIZE-1), (GRID_SIZE-1, GRID_SIZE-1)]
                        game.add_player(username, positions[len(game.players)])
                        print(f"Added player {username} to position {positions[len(game.players)-1]}")
                        
                        # Start game if we have enough players
                        if len(game.players) >= MIN_PLAYERS and not game.is_running:
                            print(f"Starting game {match_id} with {len(game.players)} players")
                            game.is_running = True
                            game.start_time = time.time()
                            game.last_gem_spawn = time.time()
                            await broadcast_game_state(match_id)

                    elif data["type"] == "move" and username:
                        direction = data["direction"]
                        print(f"Player {username} moving {direction}")
                        if game.move_player(username, direction):
                            await broadcast_game_state(match_id)

                    elif data["type"] == "get_state":
                        state = game.get_state()
                        print(f"Sending game state: {state}")
                        await websocket.send(json.dumps({
                            "type": "game_state",
                            "state": state
                        }))
                except json.JSONDecodeError as e:
                    print(f"Invalid JSON received: {e}")
                    print(f"Raw message: {message}")
                    continue
                except Exception as e:
                    print(f"Error processing message: {e}")
                    print(traceback.format_exc())
                    continue

        except websockets.ConnectionClosed as e:
            print(f"Connection closed for {username} in match {match_id}: {e}")
            if username:
                game.remove_player(username)
                await broadcast_game_state(match_id)
        except Exception as e:
            print(f"Error in game handler for match {match_id}: {e}")
            print(traceback.format_exc())
            if username:
                game.remove_player(username)
                await broadcast_game_state(match_id)
        finally:
            # Remove this websocket from connected clients
            if match_id in connected_clients and websocket in connected_clients[match_id]:
                connected_clients[match_id].remove(websocket)
                if not connected_clients[match_id]:
                    del connected_clients[match_id]
    except Exception as e:
        print(f"Fatal error in game handler: {e}")
        print(traceback.format_exc())

async def game_loop():
    """Main game loop"""
    print("\n" + "="*50)
    print("🎮 GAME SERVER IS RUNNING")
    print("="*50)
    print("Waiting for players to connect...")
    print("Press Ctrl+C to stop the server")
    print("="*50 + "\n")
    
    last_status_time = time.time()
    try:
        while True:
            current_time = time.time()
            
            # Print status every 5 seconds
            if current_time - last_status_time >= 5:
                active_games_count = len(active_games)
                total_players = sum(len(game.players) for game in active_games.values())
                print(f"\n📊 Server Status:")
                print(f"Active games: {active_games_count}")
                print(f"Total players: {total_players}")
                print(f"Uptime: {int(current_time - start_time)} seconds")
                print("-"*30)
                last_status_time = current_time
            
            for match_id, game in list(active_games.items()):
                if not game.is_running:
                    continue

                # Spawn gems periodically
                if current_time - game.last_gem_spawn >= GEM_SPAWN_INTERVAL:
                    game.spawn_gem()
                    game.last_gem_spawn = current_time
                    print(f"💎 Spawned gem in match {match_id}")
                    await broadcast_game_state(match_id)

                # Check for game over
                if game.is_game_over():
                    print(f"🏁 Game {match_id} is over")
                    await broadcast_game_state(match_id)
                    # Clean up game after a delay
                    await asyncio.sleep(5)
                    if match_id in active_games:
                        del active_games[match_id]

            await asyncio.sleep(0.1)  # 10Hz update rate
    except asyncio.CancelledError:
        print("\n⚠️ Game loop cancelled")
        raise
    except Exception as e:
        print(f"\n❌ Error in game loop: {e}")
        print(traceback.format_exc())
        raise

async def start_game_server():
    """Start the game server"""
    global start_time
    start_time = time.time()
    
    print("\n" + "="*50)
    print("🚀 Starting Game Server...")
    print(f"🌐 Listening on ws://0.0.0.0:9001")
    print("="*50)
    
    # Create a test game for debugging
    test_match_id = "test"
    active_games[test_match_id] = GameState(test_match_id)
    print(f"🎲 Created test game with ID: {test_match_id}")
    
    try:
        server = await serve(game_handler, "0.0.0.0", 9001)
        print("✅ Game server started successfully")
        await game_loop()
    except Exception as e:
        print(f"\n❌ Error in game server: {e}")
        print(traceback.format_exc())
    finally:
        if 'server' in locals():
            print("\n🛑 Shutting down server...")
            server.close()
            await server.wait_closed()
            print("✅ Server shutdown complete")

if __name__ == "__main__":
    try:
        asyncio.run(start_game_server())
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped by user")
    except Exception as e:
        print(f"\n❌ Error starting game server: {e}")
        print(traceback.format_exc())
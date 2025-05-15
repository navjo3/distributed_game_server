import asyncio
import json
import websockets

clients = []
game_state = {
    "players": [],
    "turn": 0,
    "hp": [100, 100],
    "game_over": False
}

async def handle_client(websocket):
    global clients, game_state
    
    # Check if game is full
    if len(clients) >= 2:
        await websocket.send(json.dumps({
            "type": "error",
            "message": "Game full"
        }))
        await websocket.close()
        return
    
    # Add new player
    player_id = len(clients)
    clients.append(websocket)
    game_state["players"].append(f"Player{player_id + 1}")
    print(f"Player{player_id + 1} connected")
    
    # Send welcome message with game state
    await websocket.send(json.dumps({
        "type": "welcome",
        "player_id": player_id,
        "name": f"Player{player_id + 1}",
        "hp": game_state["hp"],
        "turn": game_state["turn"]
    }))
    
    # If two players connected, notify first player it's their turn
    if len(clients) == 2 and player_id == 1:
        await clients[0].send(json.dumps({
            "type": "state",
            "hp": game_state["hp"],
            "turn": game_state["turn"],
            "message": "Game started! Your turn."
        }))
    
    try:
        async for message in websocket:
            data = json.loads(message)
            
            # Validate player ID
            if "player_id" not in data:
                await websocket.send(json.dumps({"type": "error", "message": "Invalid message format"}))
                continue
                
            # Check if game is already over
            if game_state["game_over"]:
                await websocket.send(json.dumps({"type": "error", "message": "Game already ended"}))
                continue
                
            # Check if it's player's turn
            if data["player_id"] != game_state["turn"]:
                await websocket.send(json.dumps({"type": "error", "message": "Not your turn"}))
                continue
            
            # Process attack
            target_id = 1 - data["player_id"]
            game_state["hp"][target_id] -= 10
            
            # Check for winner
            winner = None
            if game_state["hp"][target_id] <= 0:
                winner = game_state["players"][data["player_id"]]
                game_state["game_over"] = True
            
            # Update turn
            game_state["turn"] = target_id
            
            # Create update message
            update = {
                "type": "state",
                "attacker": game_state["players"][data["player_id"]],
                "target": game_state["players"][target_id],
                "hp": game_state["hp"],
                "turn": game_state["turn"],
                "winner": winner
            }
            
            # Broadcast to all clients
            disconnected = []
            for client in clients:
                try:
                    await client.send(json.dumps(update))
                except:
                    disconnected.append(client)
            
            # Clean up disconnected clients
            for client in disconnected:
                if client in clients:
                    clients.remove(client)
                    
    except websockets.ConnectionClosed:
        print(f"Player{player_id + 1} disconnected")
        
    except Exception as e:
        print(f"Error handling client: {e}")
        
    finally:
        # Clean up when a client disconnects
        if websocket in clients:
            clients.remove(websocket)
            print(f"Player{player_id + 1} removed from clients list")

async def main():
    async with websockets.serve(handle_client, "localhost", 8080):
        print("Server started on ws://localhost:8080")
        await asyncio.Future()  # Run forever

asyncio.run(main())
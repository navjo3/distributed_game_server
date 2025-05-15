import asyncio
import json
import websockets
import aioconsole  # Need to install this with: pip install aioconsole

async def play():
    uri = "ws://localhost:8080"
    
    try:
        async with websockets.connect(uri) as websocket:
            welcome_msg = await websocket.recv()
            welcome = json.loads(welcome_msg)
            
            if welcome.get("type") == "error":
                print(f"[ERROR] Server error: {welcome['message']}")
                return
                
            if welcome.get("type") != "welcome":
                print("[ERROR] Unexpected server response.")
                return
                
            player_id = welcome["player_id"]
            name = welcome["name"]
            print(f"[CONNECTED] Connected as {name}")
            print(f"[HP] Starting HP: {welcome['hp']}")
            print(f"[TURN] It is {'your' if welcome['turn'] == player_id else 'opponents'} turn")
            
            # Flags to control game flow
            is_my_turn = welcome['turn'] == player_id
            game_running = True
            
            async def receiver():
                nonlocal is_my_turn, game_running
                
                try:
                    async for msg in websocket:
                        data = json.loads(msg)
                        
                        if data["type"] == "state":
                            if "attacker" in data:
                                print(f"\n[ATTACK] {data['attacker']} attacked {data['target']}")
                            
                            print(f"[HP] HP: {data['hp']}")
                            
                            # Update turn status
                            is_my_turn = data["turn"] == player_id
                            
                            if data.get("winner"):
                                print(f"\n[WINNER] {data['winner']} wins!")
                                game_running = False
                                return
                                
                            if is_my_turn:
                                print("[TURN] Your turn! Press ENTER to attack.")
                            else:
                                print("[WAITING] Waiting for opponent's move...")
                                
                        elif data["type"] == "error":
                            print(f"[WARNING] {data['message']}")
                except Exception as e:
                    print(f"Error in receiver: {e}")
                    game_running = False
            
            async def sender():
                nonlocal is_my_turn, game_running
                
                try:
                    while game_running:
                        if is_my_turn:
                            # Use aioconsole instead of regular input to avoid blocking
                            await aioconsole.ainput(">> Press ENTER to attack: ")
                            
                            if not game_running:
                                break
                                
                            move = {
                                "player_id": player_id,
                                "action": "attack"
                            }
                            
                            await websocket.send(json.dumps(move))
                            is_my_turn = False  # Temporarily set to false until confirmed by server
                        else:
                            # Small sleep to prevent CPU spinning while waiting
                            await asyncio.sleep(0.1)
                except Exception as e:
                    print(f"Error in sender: {e}")
                    game_running = False
            
            try:
                # Start both tasks
                sender_task = asyncio.create_task(sender())
                receiver_task = asyncio.create_task(receiver())
                
                # Wait for either task to complete
                await asyncio.gather(receiver_task, sender_task)
            except Exception as e:
                print(f"[ERROR] Task error: {e}")
            
    except websockets.ConnectionClosed:
        print("[ERROR] Connection to server closed")
    except Exception as e:
        print(f"[ERROR] Error: {e}")

print("[GAME] Simple Combat Game Client")
print("===========================")
asyncio.run(play())
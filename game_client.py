import asyncio
import pygame
import websockets
import json
import sys

# Game constants
WIDTH, HEIGHT = 800, 600
PLAYER_SIZE = 20
FPS = 60
MOVE_SPEED = 5

# Game state
player_id = None
players = {}
connected = False

async def connect_to_server():
    global player_id, players, connected
    
    uri = "ws://localhost:9001"
    try:
        async with websockets.connect(uri) as ws:
            connected = True
            print("Connected to game server!")
            
            async def send_input():
                while True:
                    keys = pygame.key.get_pressed()
                    if player_id and player_id in players:
                        current_pos = players[player_id]
                        new_x, new_y = current_pos['x'], current_pos['y']
                        
                        if keys[pygame.K_UP]:
                            new_y -= MOVE_SPEED
                        if keys[pygame.K_DOWN]:
                            new_y += MOVE_SPEED
                        if keys[pygame.K_LEFT]:
                            new_x -= MOVE_SPEED
                        if keys[pygame.K_RIGHT]:
                            new_x += MOVE_SPEED
                            
                        # Keep player within screen bounds
                        new_x = max(0, min(WIDTH - PLAYER_SIZE, new_x))
                        new_y = max(0, min(HEIGHT - PLAYER_SIZE, new_y))
                        
                        if new_x != current_pos['x'] or new_y != current_pos['y']:
                            await ws.send(json.dumps({
                                "type": "move",
                                "id": player_id,
                                "x": new_x,
                                "y": new_y
                            }))
                    
                    await asyncio.sleep(1 / FPS)

            async def receive_updates():
                global player_id
                async for message in ws:
                    data = json.loads(message)
                    if data["type"] == "init":
                        player_id = data["id"]
                        print(f"Received player ID: {player_id}")
                    elif data["type"] == "state":
                        players.clear()
                        players.update(data["players"])

            await asyncio.gather(send_input(), receive_updates())
    except websockets.exceptions.ConnectionClosed:
        print("Connection to server lost!")
        connected = False
    except Exception as e:
        print(f"Error: {e}")
        connected = False

def run_game():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Multiplayer Game Client")
    clock = pygame.time.Clock()

    loop = asyncio.get_event_loop()
    asyncio.ensure_future(connect_to_server())

    running = True
    while running:
        clock.tick(FPS)
        screen.fill((30, 30, 30))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # Draw connection status
        font = pygame.font.Font(None, 36)
        status_text = "Connected" if connected else "Disconnected"
        status_color = (0, 255, 0) if connected else (255, 0, 0)
        text_surface = font.render(status_text, True, status_color)
        screen.blit(text_surface, (10, 10))

        # Draw all players
        for pid, pos in players.items():
            color = (0, 255, 0) if pid == player_id else (255, 0, 0)
            pygame.draw.rect(screen, color, (pos["x"], pos["y"], PLAYER_SIZE, PLAYER_SIZE))

        pygame.display.flip()
        loop.run_until_complete(asyncio.sleep(0))  # Let asyncio run

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    run_game() 
import tkinter as tk
from tkinter import messagebox, ttk
import requests
import asyncio
import threading
import json
import websockets
import traceback
import uuid
import sys
import os

# Server configuration - can be set via environment variables
<<<<<<< HEAD
SERVER_HOST = os.environ.get("SERVER_HOST", "localhost")  # Change this to your cloud server's IP/domain
SERVER_HTTP_PORT = os.environ.get("SERVER_HTTP_PORT", "5000")
SERVER_WS_PORT = os.environ.get("SERVER_WS_PORT", "8765")

# API endpoints
MASTER_API = f"http://192.168.213.236:5000"
MATCHMAKING_WS = f"ws://192.168.213.236:8765"
=======
SERVER_HOST = os.environ.get("SERVER_HOST", "localhost")
SERVER_HTTP_PORT = os.environ.get("SERVER_HTTP_PORT", "5000")
SERVER_WS_PORT = os.environ.get("SERVER_WS_PORT", "8765")
GAME_SERVER_PORT = os.environ.get("GAME_SERVER_PORT", "9001")

# API endpoints
MASTER_API = f"http://{SERVER_HOST}:{SERVER_HTTP_PORT}"
MATCHMAKING_WS = f"ws://{SERVER_HOST}:{SERVER_WS_PORT}"
GAME_SERVER_WS = f"ws://{SERVER_HOST}:{GAME_SERVER_PORT}"
>>>>>>> 1c9a33f (reverting changes)

def debug_print(*args, **kwargs):
    print("[DEBUG]", *args, **kwargs)
    sys.stdout.flush()

class GameClientApp:
    def __init__(self, root):
        self.root = root
<<<<<<< HEAD
        self.root.title("Distributed Game Client")
        
        # Add server connection info
        debug_print(f"Connecting to server at {MASTER_API}")
        debug_print(f"WebSocket endpoint at {MATCHMAKING_WS}")
        
=======
        self.root.title("Gem Hunt")
        
        # Game state
>>>>>>> 1c9a33f (reverting changes)
        self.username = None
        self.match_info = None
        self.room_code = None
        self.is_host = False
        self.matchmaking_active = False
        self.websocket = None
        self.game_state = None
        self.running = False
        
        # Verify server connection before starting
        if self.check_server():
            self.init_main_screen()
        else:
            self.show_connection_error()

    def check_server(self):
        try:
            debug_print("Checking server connection...")
            response = requests.get(f"{MASTER_API}/health", timeout=5)
            debug_print(f"Server response status: {response.status_code}")
            debug_print(f"Server response content: {response.text}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    debug_print(f"Parsed JSON response: {data}")
                    return data.get("status") == "ok"
                except json.JSONDecodeError as je:
                    debug_print(f"JSON decode error: {je}")
                    return False
            return False
        except requests.exceptions.RequestException as e:
            debug_print(f"Connection error: {e}")
            return False

    def show_connection_error(self):
        self.clear_screen()
        tk.Label(self.root, text="⚠️ Server Connection Error", font=('Arial', 14, 'bold')).pack(pady=20)
        tk.Label(self.root, text="Could not connect to the game server at:").pack()
        tk.Label(self.root, text=f"{MASTER_API}", font=('Arial', 10, 'italic')).pack(pady=5)
        
        # Add server configuration frame
        config_frame = tk.Frame(self.root)
        config_frame.pack(pady=20, padx=20)
        
        tk.Label(config_frame, text="Server Host:").grid(row=0, column=0, sticky="e", padx=5)
        self.host_entry = tk.Entry(config_frame)
        self.host_entry.insert(0, SERVER_HOST)
        self.host_entry.grid(row=0, column=1, sticky="w")
        
        tk.Label(config_frame, text="HTTP Port:").grid(row=1, column=0, sticky="e", padx=5)
        self.http_port_entry = tk.Entry(config_frame)
        self.http_port_entry.insert(0, SERVER_HTTP_PORT)
        self.http_port_entry.grid(row=1, column=1, sticky="w")
        
        tk.Label(config_frame, text="WebSocket Port:").grid(row=2, column=0, sticky="e", padx=5)
        self.ws_port_entry = tk.Entry(config_frame)
        self.ws_port_entry.insert(0, SERVER_WS_PORT)
        self.ws_port_entry.grid(row=2, column=1, sticky="w")
        
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=10)
        
        tk.Button(button_frame, text="Update & Retry", command=self.update_server_config).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Exit", command=self.root.quit).pack(side=tk.LEFT, padx=5)

    def update_server_config(self):
        global MASTER_API, MATCHMAKING_WS, SERVER_HOST, SERVER_HTTP_PORT, SERVER_WS_PORT
        
        SERVER_HOST = self.host_entry.get().strip()
        SERVER_HTTP_PORT = self.http_port_entry.get().strip()
        SERVER_WS_PORT = self.ws_port_entry.get().strip()
        
        MASTER_API = f"http://{SERVER_HOST}:{SERVER_HTTP_PORT}"
        MATCHMAKING_WS = f"ws://{SERVER_HOST}:{SERVER_WS_PORT}"
        
        debug_print(f"Updated server configuration:")
        debug_print(f"MASTER_API: {MASTER_API}")
        debug_print(f"MATCHMAKING_WS: {MATCHMAKING_WS}")
        
        if self.check_server():
            self.init_main_screen()
        else:
            messagebox.showerror("Connection Error", "Could not connect to the server with the new configuration.")

    def clear_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def init_main_screen(self):
        self.clear_screen()

        # Username entry
        tk.Label(self.root, text="Username:").pack(pady=(20,5))
        self.username_entry = tk.Entry(self.root)
        self.username_entry.pack()

        # Buttons frame
        buttons_frame = tk.Frame(self.root)
        buttons_frame.pack(pady=20)
        
        # Join random matchmaking button
        tk.Button(
            buttons_frame, 
            text="Join Random Match", 
            command=self.join_random_match
        ).pack(side=tk.LEFT, padx=5)
        
        # Create room button
        tk.Button(
            buttons_frame, 
            text="Create Room", 
            command=self.create_room
        ).pack(side=tk.LEFT, padx=5)
        
        # Join specific room option
        tk.Label(self.root, text="Room Code:").pack()
        room_frame = tk.Frame(self.root)
        room_frame.pack(pady=10)
        
        self.room_code_entry = tk.Entry(room_frame, width=10)
        self.room_code_entry.pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            room_frame, 
            text="Join Room", 
            command=self.join_specific_room
        ).pack(side=tk.LEFT)

    def join_random_match(self):
        username = self.username_entry.get().strip()
        if not username:
            messagebox.showerror("Error", "Please enter a username.")
            return
        
        self.username = username
        self.room_code = None
        self.is_host = False
        
        self.join_master_server("random")

    def create_room(self):
        username = self.username_entry.get().strip()
        if not username:
            messagebox.showerror("Error", "Please enter a username.")
            return
        
        try:
            response = requests.post(f"{MASTER_API}/create_room", 
                                    json={"username": username},
                                    headers={"Content-Type": "application/json"})
            
            data = response.json()
            if data["success"]:
                self.username = username
                self.room_code = data["room_code"]
                self.is_host = True
                
                self.join_master_server("host")
            else:
                messagebox.showerror("Error", data["message"])
                
        except Exception as e:
            print(f"Connection error: {str(e)}")
            print(traceback.format_exc())
            messagebox.showerror("Connection Error", str(e))

    def join_specific_room(self):
        username = self.username_entry.get().strip()
        room_code = self.room_code_entry.get().strip()
        
        if not username:
            messagebox.showerror("Error", "Please enter a username.")
            return
            
        if not room_code:
            messagebox.showerror("Error", "Please enter a room code.")
            return
        
        self.username = username
        self.room_code = room_code
        self.is_host = False
        
        self.join_master_server("join")

    def join_master_server(self, join_type):
        try:
            response = requests.post(f"{MASTER_API}/join", 
                                   json={"username": self.username},
                                   headers={"Content-Type": "application/json"})
            
            try:
                data = response.json()
                if data["success"]:
                    if join_type == "host":
                        self.init_room_screen()
                    else:
                        self.init_matchmaking_screen()
                else:
                    messagebox.showerror("Join Failed", data["message"])
            except json.JSONDecodeError as je:
                print(f"Server response: {response.text}")
                messagebox.showerror("Error", f"Invalid server response: {str(je)}")
        except Exception as e:
            print(f"Connection error: {str(e)}")
            print(traceback.format_exc())
            messagebox.showerror("Connection Error", str(e))

    def init_matchmaking_screen(self):
        self.clear_screen()

        # Header display
        header_text = f"Welcome, {self.username}!"
        if self.room_code:
            header_text += f"\nJoining Room: {self.room_code}"
        else:
            header_text += "\nJoining Random Match"
            
        tk.Label(self.root, text=header_text, font=("Helvetica", 12)).pack(pady=10)
        
        # Players info
        self.players_frame = tk.Frame(self.root)
        self.players_frame.pack(pady=10, fill=tk.X, padx=20)
        
        tk.Label(self.players_frame, text="Players in lobby:", font=("Helvetica", 10, "bold")).grid(row=0, column=0, sticky=tk.W)
        
        self.players_list = tk.Listbox(self.players_frame, height=6, width=25)
        self.players_list.grid(row=1, column=0, pady=5)
        
        # Status message
        self.waiting_label = tk.Label(self.root, text="Waiting for players...")
        self.waiting_label.pack()
        
        # Room code display (if applicable)
        if self.room_code:
            room_frame = tk.Frame(self.root)
            room_frame.pack(pady=5)
            tk.Label(room_frame, text="Room Code:").pack(side=tk.LEFT)
            tk.Label(room_frame, text=self.room_code, font=("Helvetica", 12, "bold")).pack(side=tk.LEFT, padx=5)
            
        # Cancel button
        tk.Button(self.root, text="Cancel", command=self.cancel_matchmaking).pack(pady=10)
        
        self.root.update()

        # Start matchmaking in background
        self.matchmaking_loop = asyncio.new_event_loop()
        self.matchmaking_active = True
        threading.Thread(target=self.start_matchmaking, daemon=True).start()

    def init_room_screen(self):
        self.clear_screen()

        # Header display
        header_text = f"Welcome, {self.username}!\nYou are the Host"
        tk.Label(self.root, text=header_text, font=("Helvetica", 12, "bold")).pack(pady=10)
        
        # Room code display
        room_frame = tk.Frame(self.root)
        room_frame.pack(pady=5)
        tk.Label(room_frame, text="Room Code:").pack(side=tk.LEFT)
        tk.Label(room_frame, text=self.room_code, font=("Helvetica", 14, "bold")).pack(side=tk.LEFT, padx=5)
        
        tk.Label(self.root, text="Share this code with other players").pack()
        
        # Players info
        self.players_frame = tk.Frame(self.root)
        self.players_frame.pack(pady=10, fill=tk.X, padx=20)
        
        tk.Label(self.players_frame, text="Players in room:", font=("Helvetica", 10, "bold")).grid(row=0, column=0, sticky=tk.W)
        
        self.players_list = tk.Listbox(self.players_frame, height=6, width=25)
        self.players_list.grid(row=1, column=0, pady=5)
        self.players_list.insert(tk.END, f"{self.username} (Host)")
        
        # Status message
        self.waiting_label = tk.Label(self.root, text="Waiting for players to join...")
        self.waiting_label.pack()
        
        # Button frame
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=10)
        
        # Start game button (initially disabled)
        self.start_button = tk.Button(button_frame, text="Start Game", command=self.start_game, state=tk.DISABLED)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        # Cancel button
        tk.Button(button_frame, text="Cancel", command=self.cancel_matchmaking).pack(side=tk.LEFT, padx=5)
        
        self.root.update()

        # Start room hosting in background
        self.matchmaking_loop = asyncio.new_event_loop()
        self.matchmaking_active = True
        threading.Thread(target=self.start_matchmaking, daemon=True).start()

    def update_players_list(self, players, host=None):
        self.players_list.delete(0, tk.END)
        
        for player in players:
            display_name = player
            if host and player == host:
                display_name += " (Host)"
            self.players_list.insert(tk.END, display_name)
            
        # If host, enable start button when we have at least 2 players
        if self.is_host and len(players) >= 2:
            self.start_button.config(state=tk.NORMAL)
        elif self.is_host:
            self.start_button.config(state=tk.DISABLED)

    def update_waiting_label(self, players_needed):
        if players_needed == 0:
            text = "Lobby full! Game starting soon..."
        elif players_needed == 1:
            text = "Waiting for 1 more player..."
        else:
            text = f"Waiting for {players_needed} more players..."
        self.waiting_label.config(text=text)

    def cancel_matchmaking(self):
        self.matchmaking_active = False
        self.init_main_screen()

    def start_game(self):
        if self.websocket and self.is_host:
            asyncio.run_coroutine_threadsafe(
                self.send_start_game(), 
                self.matchmaking_loop
            )

    async def send_start_game(self):
        if self.websocket:
            start_data = {
                "type": "start_game",
                "username": self.username,
                "room_code": self.room_code
            }
            await self.websocket.send(json.dumps(start_data))

    async def matchmaking_coroutine(self):
        try:
            async with websockets.connect(MATCHMAKING_WS) as ws:
                self.websocket = ws
                
                if self.is_host and self.room_code:
                    # Create room message
                    join_data = {
                        "type": "create_room",
                        "username": self.username,
                        "room_code": self.room_code
                    }
                else:
                    # Join matchmaking message
                    join_data = {
                        "type": "join_match",
                        "username": self.username
                    }
                    if self.room_code:
                        join_data["room_code"] = self.room_code
                
                try:
                    await ws.send(json.dumps(join_data))
                except Exception as e:
                    print(f"Error sending join data: {str(e)}")
                    raise

                async for msg in ws:
                    if not self.matchmaking_active:
                        return
                    
                    try:
                        data = json.loads(msg)
                        
                        if data.get("type") == "error":
                            self.root.after(0, lambda: messagebox.showerror("Error", data["message"]))
                            self.root.after(0, self.init_main_screen)
                            return
                            
                        elif data.get("type") == "match_found":
                            self.match_info = data
                            self.root.after(0, self.show_game_screen)
                            return
                            
                        elif data.get("type") == "queue_update":
                            players_needed = data.get("players_needed", 0)
                            players = data.get("players", [])
                            host = data.get("host")
                            
                            self.root.after(0, lambda: self.update_waiting_label(players_needed))
                            self.root.after(0, lambda: self.update_players_list(players, host))
                            
                        elif data.get("type") == "room_created":
                            players = data.get("players", [])
                            self.root.after(0, lambda: self.update_players_list(players, self.username))
                            
                    except json.JSONDecodeError as je:
                        print(f"Invalid message received: {msg}")
                        print(f"JSON error: {str(je)}")

        except Exception as e:
            if self.matchmaking_active:  # Only show error if we haven't cancelled
                print(f"Matchmaking error: {str(e)}")
                print(traceback.format_exc())
                self.root.after(0, lambda: messagebox.showerror("Error", f"Matchmaking error: {str(e)}"))
                self.root.after(0, self.init_main_screen)

    def start_matchmaking(self):
        try:
            self.matchmaking_loop.run_until_complete(self.matchmaking_coroutine())
        except Exception as e:
            print(f"Error in matchmaking thread: {str(e)}")
            print(traceback.format_exc())
        finally:
            self.matchmaking_loop.close()
            self.websocket = None

    def show_game_screen(self):
        self.clear_screen()
        self.running = True

        # Game info frame
        info_frame = ttk.Frame(self.root)
        info_frame.pack(pady=5, padx=10, fill=tk.X)
        
        self.time_label = ttk.Label(info_frame, text="Time: 60")
        self.time_label.pack(side=tk.LEFT, padx=5)
        
        self.score_label = ttk.Label(info_frame, text="Score: 0")
        self.score_label.pack(side=tk.LEFT, padx=5)

        # Game grid frame
        self.grid_frame = ttk.Frame(self.root)
        self.grid_frame.pack(pady=10, padx=10)
        
        # Controls info
        controls_frame = ttk.Frame(self.root)
        controls_frame.pack(pady=5)
        ttk.Label(controls_frame, text="Controls: W (Up) | A (Left) | S (Down) | D (Right)").pack()

        # Bind keyboard controls
        self.root.bind('w', lambda e: self.send_move("up"))
        self.root.bind('a', lambda e: self.send_move("left"))
        self.root.bind('s', lambda e: self.send_move("down"))
        self.root.bind('d', lambda e: self.send_move("right"))
        
        # Also bind arrow keys for convenience
        self.root.bind('<Up>', lambda e: self.send_move("up"))
        self.root.bind('<Left>', lambda e: self.send_move("left"))
        self.root.bind('<Down>', lambda e: self.send_move("down"))
        self.root.bind('<Right>', lambda e: self.send_move("right"))

        # Start game connection
        threading.Thread(target=self.connect_to_game, daemon=True).start()

    def connect_to_game(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._connect_to_game())
        finally:
            loop.close()

    async def _connect_to_game(self):
        try:
            # Fix the URL format - remove the extra /game/ part as it's already in the path
            game_server_url = f"{GAME_SERVER_WS}/game/{self.match_info['match_id']}"
            print(f"Connecting to game server at: {game_server_url}")
            self.websocket = await websockets.connect(game_server_url)
            await self.websocket.send(json.dumps({
                "type": "join",
                "username": self.username
            }))

            while self.running:
                message = await self.websocket.recv()
                data = json.loads(message)
                
                if data["type"] == "game_state":
                    self.root.after(0, lambda: self.update_game_state(data["state"]))
                elif data["type"] == "error":
                    self.root.after(0, lambda: messagebox.showerror("Error", data["message"]))
                    self.running = False
                    break

        except Exception as e:
            error_msg = str(e)
            print(f"Game connection error: {error_msg}")
            print(traceback.format_exc())
            self.root.after(0, lambda: messagebox.showerror("Error", f"Game connection error: {error_msg}"))
            self.running = False

    def send_move(self, direction: str):
        if self.websocket:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self._send_move(direction))
            finally:
                loop.close()

    async def _send_move(self, direction: str):
        try:
            await self.websocket.send(json.dumps({
                "type": "move",
                "direction": direction
            }))
        except Exception as e:
            print(f"Error sending move: {str(e)}")
            print(traceback.format_exc())

    def update_game_state(self, state):
        # Update time
        self.time_label.config(text=f"Time: {int(state['time_remaining'])}")
        
        # Update scores
        scores = [f"{player}: {data['score']}" for player, data in state["players"].items()]
        self.score_label.config(text=" | ".join(scores))
        
        # Update grid
        for widget in self.grid_frame.winfo_children():
            widget.destroy()
            
        grid = state["grid"]
        players = state["players"]
        
        for y in range(len(grid)):
            for x in range(len(grid[0])):
                cell = ttk.Frame(self.grid_frame, width=30, height=30, relief="solid", borderwidth=1)
                cell.grid(row=y, column=x)
                
                if grid[y][x] == 1:
                    ttk.Label(cell, text="💎").place(relx=0.5, rely=0.5, anchor="center")
                
                for player, data in players.items():
                    if data["position"] == (x, y):
                        ttk.Label(cell, text=player[0].upper()).place(relx=0.5, rely=0.5, anchor="center")
        
        if state.get("game_over"):
            messagebox.showinfo("Game Over", f"Winner: {state.get('winner')}")
            self.running = False
            self.root.quit()

    def _update_game_state(self, state):
        """Update the game state display"""
        print(f"Updating game state: {state}")
        self.game_state = state
        
        # Update score labels
        for player, score in state["scores"].items():
            if player in self.score_labels:
                self.score_labels[player].config(text=f"{player}: {score}")
        
        # Update time remaining
        time_left = max(0, int(state["time_remaining"]))
        self.time_label.config(text=f"Time: {time_left}s")
        
        # Update grid
        for i in range(10):
            for j in range(10):
                cell = self.grid_cells[i][j]
                cell.config(text="")
                cell.config(bg="white")
        
        # Draw gems
        for gem in state["gems"]:
            x, y = gem
            self.grid_cells[y][x].config(text="💎")
        
        # Draw players
        for player, pos in state["positions"].items():
            x, y = pos
            cell = self.grid_cells[y][x]
            cell.config(text="👤")
            cell.config(bg="lightblue")
        
        # Check for game over
        if state.get("game_over"):
            winner = state.get("winner")
            if winner:
                messagebox.showinfo("Game Over", f"Game Over! {winner} wins!")
            else:
                messagebox.showinfo("Game Over", "Game Over! It's a tie!")
            self._show_matchmaking()

    async def _receive_messages(self):
        """Receive and handle messages from the server"""
        try:
            async for message in self.ws:
                data = json.loads(message)
                print(f"Received message: {data}")
                
                if data["type"] == "game_state":
                    # Update game state in the main thread
                    self.root.after(0, lambda s=data["state"]: self._update_game_state(s))
                elif data["type"] == "error":
                    messagebox.showerror("Error", data["message"])
                    self._show_matchmaking()
        except Exception as e:
            print(f"Error receiving messages: {e}")
            print(traceback.format_exc())
            error_msg = str(e)
            self.root.after(0, lambda: messagebox.showerror("Connection Error", f"Lost connection to game server: {error_msg}"))
            self._show_matchmaking()

    def run(self):
        self.root.mainloop()
        self.running = False
        if self.websocket:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.websocket.close())
            finally:
                loop.close()

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("400x500")
    app = GameClientApp(root)
    app.run()
import tkinter as tk
from tkinter import ttk, messagebox
import asyncio
import websockets
import json
import threading
import traceback
import sys
import os

# Server configuration
SERVER_HOST = os.environ.get("SERVER_HOST", "localhost")
SERVER_HTTP_PORT = os.environ.get("SERVER_HTTP_PORT", "5000")
SERVER_WS_PORT = os.environ.get("SERVER_WS_PORT", "8765")
GAME_SERVER_PORT = os.environ.get("GAME_SERVER_PORT", "9001")

# API endpoints
MASTER_API = f"http://{SERVER_HOST}:{SERVER_HTTP_PORT}"
MATCHMAKING_WS = f"ws://{SERVER_HOST}:{SERVER_WS_PORT}"
GAME_SERVER_WS = f"ws://{SERVER_HOST}:{GAME_SERVER_PORT}"

class GameClient:
    def __init__(self, root):
        self.root = root
        self.root.title("Gem Hunt")
        
        # Game state
        self.username = None
        self.match_info = None
        self.room_code = None
        self.is_host = False
        self.matchmaking_active = False
        self.websocket = None
        self.game_state = None
        self.running = False
        
        # Initialize UI
        self.init_main_screen()

    def init_main_screen(self):
        self.clear_screen()
        
        # Username entry
        ttk.Label(self.root, text="Username:").pack(pady=(20,5))
        self.username_entry = ttk.Entry(self.root)
        self.username_entry.pack()
        
        # Buttons frame
        buttons_frame = ttk.Frame(self.root)
        buttons_frame.pack(pady=20)
        
        ttk.Button(buttons_frame, text="Create Room", command=self.create_room).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Join Random", command=self.join_random).pack(side=tk.LEFT, padx=5)
        
        # Room code entry
        room_frame = ttk.Frame(self.root)
        room_frame.pack(pady=10)
        ttk.Label(room_frame, text="Room Code:").pack(side=tk.LEFT)
        self.room_code_entry = ttk.Entry(room_frame)
        self.room_code_entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(room_frame, text="Join Room", command=self.join_room).pack(side=tk.LEFT, padx=5)

    def clear_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def create_room(self):
        username = self.username_entry.get().strip()
        if not username:
            messagebox.showerror("Error", "Please enter a username")
            return
            
        self.username = username
        self.is_host = True
        self.start_matchmaking("create")

    def join_room(self):
        username = self.username_entry.get().strip()
        room_code = self.room_code_entry.get().strip()
        
        if not username:
            messagebox.showerror("Error", "Please enter a username")
            return
        if not room_code:
            messagebox.showerror("Error", "Please enter a room code")
            return
            
        self.username = username
        self.room_code = room_code
        self.is_host = False
        self.start_matchmaking("join")

    def join_random(self):
        username = self.username_entry.get().strip()
        if not username:
            messagebox.showerror("Error", "Please enter a username")
            return
            
        self.username = username
        self.room_code = None
        self.is_host = False
        self.start_matchmaking("random")

    def start_matchmaking(self, join_type):
        self.clear_screen()
        self.matchmaking_active = True
        
        # Status display
        ttk.Label(self.root, text=f"Connecting as {self.username}...").pack(pady=20)
        
        # Start matchmaking in background
        threading.Thread(target=self.matchmaking_thread, args=(join_type,), daemon=True).start()

    def matchmaking_thread(self, join_type):
        asyncio.run(self.matchmaking_coroutine(join_type))

    async def matchmaking_coroutine(self, join_type):
        try:
            async with websockets.connect(MATCHMAKING_WS) as ws:
                self.websocket = ws
                
                if join_type == "create":
                    await ws.send(json.dumps({
                        "type": "create_room",
                        "username": self.username
                    }))
                elif join_type == "join":
                    await ws.send(json.dumps({
                        "type": "join_match",
                        "username": self.username,
                        "room_code": self.room_code
                    }))
                else:  # random
                    await ws.send(json.dumps({
                        "type": "join_match",
                        "username": self.username
                    }))

                while self.matchmaking_active:
                    message = await ws.recv()
                    data = json.loads(message)
                    
                    if data["type"] == "error":
                        self.root.after(0, lambda: messagebox.showerror("Error", data["message"]))
                        self.root.after(0, self.init_main_screen)
                        break
                    elif data["type"] == "match_found":
                        self.match_info = data
                        self.root.after(0, self.show_game_screen)
                        break
                    elif data["type"] == "queue_update":
                        self.root.after(0, lambda: self.update_queue_status(data))
                        
        except Exception as e:
            print(f"Matchmaking error: {str(e)}")
            print(traceback.format_exc())
            self.root.after(0, lambda: messagebox.showerror("Error", f"Matchmaking error: {str(e)}"))
            self.root.after(0, self.init_main_screen)

    def update_queue_status(self, data):
        self.clear_screen()
        ttk.Label(self.root, text=f"Waiting for players...").pack(pady=10)
        ttk.Label(self.root, text=f"Players needed: {data.get('players_needed', 0)}").pack()
        
        if data.get("players"):
            ttk.Label(self.root, text="Players in room:").pack(pady=10)
            for player in data["players"]:
                ttk.Label(self.root, text=f"• {player}").pack()

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
        
        # Movement buttons frame
        movement_frame = ttk.Frame(self.root)
        movement_frame.pack(pady=10)
        
        ttk.Button(movement_frame, text="↑", command=lambda: self.send_move("up")).grid(row=0, column=1)
        ttk.Button(movement_frame, text="←", command=lambda: self.send_move("left")).grid(row=1, column=0)
        ttk.Button(movement_frame, text="→", command=lambda: self.send_move("right")).grid(row=1, column=2)
        ttk.Button(movement_frame, text="↓", command=lambda: self.send_move("down")).grid(row=2, column=1)

        # Start game connection
        threading.Thread(target=self.connect_to_game, daemon=True).start()

    def connect_to_game(self):
        asyncio.run(self._connect_to_game())

    async def _connect_to_game(self):
        try:
            self.websocket = await websockets.connect(f"{GAME_SERVER_WS}/game/{self.match_info['match_id']}")
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
            # Create a new event loop for this thread
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

    def run(self):
        self.root.mainloop()
        self.running = False
        if self.websocket:
            asyncio.run(self.websocket.close())

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("400x500")
    app = GameClient(root)
    app.run()
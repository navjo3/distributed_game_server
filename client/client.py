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

MASTER_API = "http://localhost:5000"
MATCHMAKING_WS = "ws://localhost:8765"

def debug_print(*args, **kwargs):
    print("[DEBUG]", *args, **kwargs)
    sys.stdout.flush()

class GameClientApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Distributed Game Client")
        self.username = None
        self.match_info = None
        self.room_code = None
        self.is_host = False
        self.matchmaking_active = False
        self.websocket = None
        
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
        tk.Label(self.root, text="Could not connect to the game server.").pack()
        tk.Label(self.root, text="Please ensure the server is running at:").pack(pady=10)
        tk.Label(self.root, text=f"{MASTER_API}", font=('Arial', 10, 'italic')).pack()
        
        tk.Button(self.root, text="Retry Connection", command=self.retry_connection).pack(pady=20)
        tk.Button(self.root, text="Exit", command=self.root.quit).pack()

    def retry_connection(self):
        if self.check_server():
            self.init_main_screen()
        else:
            messagebox.showerror("Connection Error", "Could not connect to the server. Please ensure it is running.")

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

        tk.Label(self.root, text="🎮 Match Started!", font=("Helvetica", 16, "bold")).pack(pady=10)
        
        # Match info
        info_frame = tk.Frame(self.root)
        info_frame.pack(pady=10, padx=20, fill=tk.X)
        
        tk.Label(info_frame, text=f"Match ID: {self.match_info['match_id']}", anchor="w").pack(fill=tk.X)
        tk.Label(info_frame, text=f"Game Server: {self.match_info['game_server']}", anchor="w").pack(fill=tk.X)
        
        # Host info
        host_name = self.match_info['host']
        host_status = " (You)" if host_name == self.username else ""
        tk.Label(info_frame, text=f"Host: {host_name}{host_status}", anchor="w").pack(fill=tk.X)
        
        # Players list
        tk.Label(self.root, text="Players:", font=("Helvetica", 10, "bold")).pack(anchor="w", padx=20)
        
        players_frame = tk.Frame(self.root)
        players_frame.pack(pady=5, padx=20, fill=tk.X)
        
        for player in self.match_info['players']:
            you_tag = " (You)" if player == self.username else ""
            host_tag = " (Host)" if player == self.match_info['host'] else ""
            tag = you_tag or host_tag
            tk.Label(players_frame, text=f"• {player}{tag}", anchor="w").pack(fill=tk.X)

        # Exit button
        tk.Button(self.root, text="Exit", command=self.root.quit).pack(pady=20)

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("350x400")
    app = GameClientApp(root)
    root.mainloop()
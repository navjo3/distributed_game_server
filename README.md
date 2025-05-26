# Distributed Game Server

A distributed multiplayer game system with both Pygame and Tkinter clients.

## Project Structure

```
distributed_game_server/
├── game_server/           # Game server implementation
│   └── game.py           # Main game server logic
├── client/               # Client implementations
│   ├── pygame_client.py  # Pygame-based client
│   └── tkinter_client.py # Tkinter-based client (GUI)
├── master_server/        # Master server for matchmaking
│   └── server.py        # Matchmaking server
└── requirements.txt      # Project dependencies
```

## Components

1. **Game Server** (`game_server/game.py`)
   - Handles real-time game state
   - Manages player connections
   - Broadcasts game updates
   - Handles player movements

2. **Pygame Client** (`client/pygame_client.py`)
   - Real-time game visualization
   - Keyboard controls
   - Smooth movement
   - Connection status display

3. **Tkinter Client** (`client/tkinter_client.py`)
   - Matchmaking interface
   - Room creation/joining
   - Game state display
   - Movement controls

4. **Master Server** (`master_server/server.py`)
   - Matchmaking service
   - Room management
   - Player pairing

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Start the master server:
```bash
python master_server/server.py
```

3. Start the game server:
```bash
python game_server/game.py
```

4. Run either client:
```bash
# For Pygame client
python client/pygame_client.py

# For Tkinter client
python client/tkinter_client.py
```

## Environment Variables

You can configure the servers using environment variables:

- `SERVER_HOST`: Server hostname (default: "localhost")
- `SERVER_HTTP_PORT`: HTTP port for master server (default: "5000")
- `SERVER_WS_PORT`: WebSocket port for matchmaking (default: "8765")
- `GAME_SERVER_PORT`: WebSocket port for game server (default: "9001")

## Features

- Real-time multiplayer gameplay
- Matchmaking system
- Room-based gameplay
- Multiple client implementations
- Smooth movement and collision detection
- Connection status monitoring
- Error handling and recovery 
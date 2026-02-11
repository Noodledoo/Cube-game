"""
FILE: network/server.py
Game server with multiplayer support and bot AI
"""

import socket
import threading
import time
import uuid
import random
import math
import os
import sys
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

# Bootstrap: Ensure package root is in sys.path for IDE execution
# When server.py is run directly, we need cube_boss_fight/ in sys.path
# so that imports like "from network.protocol import ..." work correctly.
# File is at: cube_boss_fight/network/server.py
# We need: cube_boss_fight/ in sys.path
_file_path = os.path.abspath(__file__)
_package_root = os.path.dirname(os.path.dirname(_file_path))  # Up from network/ to cube_boss_fight/
_package_root_resolved = os.path.normpath(_package_root)

# Add to sys.path if not already present (check normalized paths)
_sys_path_normalized = [os.path.normpath(p) for p in sys.path if p]
if _package_root_resolved not in _sys_path_normalized:
    sys.path.insert(0, _package_root_resolved)

from network.protocol import (
    MessageType, NetworkMessage,
    serialize_message, deserialize_message
)


@dataclass
class ConnectedPlayer:
    """Information about a connected player"""
    player_id: str
    name: str
    socket: Optional[socket.socket]
    address: tuple
    x: float = 400.0
    y: float = 300.0
    hp: float = 100.0
    max_hp: float = 100.0
    shooting: bool = False
    last_update: float = field(default_factory=time.time)
    is_bot: bool = False
    ready: bool = False


@dataclass
class ServerGameState:
    """Authoritative game state on server"""
    level: int = 1
    boss_hp: float = 500.0
    boss_max_hp: float = 500.0
    boss_x: float = 400.0
    boss_y: float = 300.0
    game_active: bool = False
    start_time: float = 0.0


class BotAI:
    """Simple bot AI for testing multiplayer"""
    
    def __init__(self, player: ConnectedPlayer):
        self.player = player
        self.target_x = random.randint(100, 700)
        self.target_y = random.randint(100, 500)
        self.move_timer = 0.0
        self.shoot_timer = 0.0
        self.dodge_timer = 0.0
        
        # AI personality
        self.aggression = random.uniform(0.3, 0.8)
        self.dodge_skill = random.uniform(0.5, 1.0)
        self.move_speed = 200 + random.randint(-50, 50)
    
    def update(self, dt: float, boss_x: float, boss_y: float, projectiles: List[Dict]):
        """Update bot behavior"""
        self.move_timer -= dt
        self.shoot_timer -= dt
        self.dodge_timer -= dt
        
        # Check for nearby projectiles and dodge
        dodge_needed = False
        dodge_dir = [0.0, 0.0]
        
        for proj in projectiles:
            dist = math.hypot(proj.get("x", 0) - self.player.x, 
                            proj.get("y", 0) - self.player.y)
            if dist < 80 * self.dodge_skill:
                dodge_needed = True
                # Move away from projectile
                dx = self.player.x - proj.get("x", 0)
                dy = self.player.y - proj.get("y", 0)
                length = math.hypot(dx, dy) or 1
                dodge_dir[0] += dx / length
                dodge_dir[1] += dy / length
        
        if dodge_needed and self.dodge_timer <= 0:
            # Quick dodge
            dodge_length = math.hypot(dodge_dir[0], dodge_dir[1]) or 1
            self.player.x += (dodge_dir[0] / dodge_length) * 100
            self.player.y += (dodge_dir[1] / dodge_length) * 100
            self.dodge_timer = 0.3
        
        # Normal movement toward target
        elif self.move_timer <= 0:
            self.target_x = random.randint(100, 700)
            self.target_y = random.randint(100, 500)
            self.move_timer = random.uniform(1.0, 3.0)
        
        # Move toward target
        dx = self.target_x - self.player.x
        dy = self.target_y - self.player.y
        dist = math.hypot(dx, dy)
        
        if dist > 10:
            speed = self.move_speed * dt
            self.player.x += (dx / dist) * speed
            self.player.y += (dy / dist) * speed
        
        # Keep in bounds
        self.player.x = max(30, min(770, self.player.x))
        self.player.y = max(30, min(570, self.player.y))
        
        # Shooting - aim at boss
        self.player.shooting = self.shoot_timer <= 0 and random.random() < self.aggression
        if self.player.shooting:
            self.shoot_timer = random.uniform(0.2, 0.5)
        
        self.player.last_update = time.time()


class GameServer:
    """Multiplayer game server with bot support"""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 5555, max_players: int = 8):
        self.host = host
        self.port = port
        self.max_players = max_players
        
        self.server_socket: Optional[socket.socket] = None
        self.running = False
        
        # Players
        self.players: Dict[str, ConnectedPlayer] = {}
        self.players_lock = threading.Lock()
        
        # Game state
        self.game_state = ServerGameState()
        
        # Bots
        self.bots: Dict[str, BotAI] = {}
        self.bot_counter = 0
        
        # Projectiles (simplified tracking)
        self.boss_projectiles: List[Dict] = []
        
        # Server info
        self.server_name = "Cube Boss Fight Server"
        self.tick_rate = 60
        self.last_tick = time.time()
    
    def start(self) -> bool:
        """Start the server"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.server_socket.settimeout(1.0)
            
            self.running = True
            
            # Start accept thread
            accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
            accept_thread.start()
            
            # Start game loop thread
            game_thread = threading.Thread(target=self._game_loop, daemon=True)
            game_thread.start()
            
            print(f"Server started on {self.host}:{self.port}")
            return True
            
        except Exception as e:
            print(f"Failed to start server: {e}")
            return False
    
    def stop(self):
        """Stop the server"""
        self.running = False
        
        # Disconnect all players
        with self.players_lock:
            for player in list(self.players.values()):
                if player.socket and not player.is_bot:
                    try:
                        player.socket.close()
                    except:
                        pass
            self.players.clear()
        
        # Close server socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        print("Server stopped")
    
    def add_bot(self, name: str = None) -> str:
        """Add a bot player to the server"""
        self.bot_counter += 1
        if name is None:
            name = f"Bot_{self.bot_counter}"
        
        player_id = f"bot_{uuid.uuid4().hex[:8]}"
        
        bot_player = ConnectedPlayer(
            player_id=player_id,
            name=name,
            socket=None,
            address=("bot", 0),
            x=random.randint(100, 700),
            y=random.randint(100, 500),
            is_bot=True,
            ready=True
        )
        
        with self.players_lock:
            self.players[player_id] = bot_player
            self.bots[player_id] = BotAI(bot_player)
        
        # Broadcast bot join
        self._broadcast(MessageType.PLAYER_JOIN, {
            "player_id": player_id,
            "name": name,
            "is_bot": True
        })
        
        # Send lobby update
        self._broadcast_lobby_update()
        
        print(f"Bot '{name}' added with ID {player_id}")
        return player_id
    
    def remove_bot(self, player_id: str = None) -> bool:
        """Remove a bot from the server. If no ID given, removes last bot."""
        with self.players_lock:
            if player_id is None:
                # Remove last added bot
                bot_ids = list(self.bots.keys())
                if not bot_ids:
                    return False
                player_id = bot_ids[-1]
            
            if player_id in self.bots:
                del self.bots[player_id]
            
            if player_id in self.players:
                player = self.players[player_id]
                del self.players[player_id]
                
                # Broadcast bot leave
                self._broadcast(MessageType.PLAYER_LEAVE, {
                    "player_id": player_id,
                    "name": player.name
                })
                
                # Send lobby update
                self._broadcast_lobby_update()
                
                print(f"Bot '{player.name}' removed")
                return True
        return False
    
    def get_bot_count(self) -> int:
        """Get number of active bots"""
        return len(self.bots)
    
    def get_player_count(self) -> int:
        """Get total number of connected players (including bots)"""
        return len(self.players)
    
    def _accept_loop(self):
        """Accept incoming connections"""
        while self.running:
            try:
                client_socket, address = self.server_socket.accept()
                
                with self.players_lock:
                    if len(self.players) >= self.max_players:
                        # Server full
                        client_socket.close()
                        continue
                
                # Handle client in new thread
                client_thread = threading.Thread(
                    target=self._handle_client, 
                    args=(client_socket, address),
                    daemon=True
                )
                client_thread.start()
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"Accept error: {e}")
    
    def _handle_client(self, client_socket: socket.socket, address: tuple):
        """Handle a connected client"""
        player_id = str(uuid.uuid4().hex[:8])
        player = ConnectedPlayer(
            player_id=player_id,
            name="Unknown",
            socket=client_socket,
            address=address
        )
        
        with self.players_lock:
            self.players[player_id] = player
        
        print(f"Player connected from {address}")
        
        player_name = "Unknown"
        try:
            while self.running:
                # Read message length
                length_data = self._recv_exact(client_socket, 4)
                if not length_data:
                    break
                
                length = int.from_bytes(length_data, 'big')
                if length > 1024 * 1024:
                    break
                
                # Read message
                message_data = self._recv_exact(client_socket, length)
                if not message_data:
                    break
                
                message = deserialize_message(message_data)
                if message:
                    print(f"Server: Received message type {message.type.name} from player {player_id}, data: {message.data}")
                    import sys
                    sys.stdout.flush()
                    self._handle_message(player_id, message)
                else:
                    print(f"Warning: Failed to deserialize message from player {player_id}")
                    import sys
                    sys.stdout.flush()
                    
        except Exception as e:
            print(f"Client error: {e}")
            import traceback
            traceback.print_exc()
            import sys
            sys.stdout.flush()
        
        # Cleanup
        with self.players_lock:
            if player_id in self.players:
                player = self.players[player_id]
                player_name = player.name
                del self.players[player_id]
                
                # Broadcast disconnect
                self._broadcast(MessageType.PLAYER_LEAVE, {
                    "player_id": player_id,
                    "name": player_name
                })
                
                # Send lobby update to remaining players
                self._broadcast_lobby_update()
        
        try:
            client_socket.close()
        except:
            pass
        
        print(f"Player {player_name} disconnected")
    
    def _recv_exact(self, sock: socket.socket, size: int) -> Optional[bytes]:
        """Receive exactly size bytes"""
        data = b''
        while len(data) < size:
            try:
                chunk = sock.recv(size - len(data))
                if not chunk:
                    return None
                data += chunk
            except:
                return None
        return data
    
    def _handle_message(self, player_id: str, message: NetworkMessage):
        """Handle a message from a player"""
        import sys
        print(f"Server: Handling message type {message.type.name} from player {player_id}", flush=True)
        sys.stdout.flush()
        with self.players_lock:
            player = self.players.get(player_id)
            if not player:
                print(f"Warning: Player {player_id} not found in players dict", flush=True)
                sys.stdout.flush()
                return
        
        if message.type == MessageType.PLAYER_JOIN:
            player.name = message.data.get("name", "Unknown")[:16]
            
            # Send player their ID
            self._send_to_player(player_id, MessageType.PLAYER_JOIN, {
                "player_id": player_id,
                "name": player.name
            })
            
            # Broadcast join
            self._broadcast(MessageType.PLAYER_JOIN, {
                "player_id": player_id,
                "name": player.name
            }, exclude=player_id)
            
            # Send current game state
            self._send_game_state(player_id)
            
            # Send lobby update to all players
            self._broadcast_lobby_update()
            
            print(f"Player '{player.name}' joined")
        
        elif message.type == MessageType.PLAYER_STATE:
            player.x = message.data.get("x", player.x)
            player.y = message.data.get("y", player.y)
            player.hp = message.data.get("hp", player.hp)
            player.shooting = message.data.get("shooting", False)
            player.last_update = time.time()
        
        elif message.type == MessageType.BOSS_HIT:
            damage = message.data.get("damage", 0)
            if self.game_state.game_active and damage > 0:
                self.game_state.boss_hp -= damage
                
                # Broadcast boss state
                self._broadcast(MessageType.BOSS_STATE, {
                    "hp": self.game_state.boss_hp,
                    "max_hp": self.game_state.boss_max_hp,
                    "x": self.game_state.boss_x,
                    "y": self.game_state.boss_y
                })
        
        elif message.type == MessageType.CHAT:
            chat_message = message.data.get("message", "")[:200]
            print(f"Server: Broadcasting chat from {player.name}: {chat_message}")
            # Broadcast to all players including sender (so they see their own message)
            self._broadcast(MessageType.CHAT, {
                "sender": player.name,
                "message": chat_message
            })
        
        elif message.type == MessageType.READY:
            player.ready = message.data.get("ready", False)
            
            # Broadcast lobby update when ready status changes
            self._broadcast_lobby_update()
            
            # Check if all ready to start
            self._check_game_start()
        
        elif message.type == MessageType.PING:
            self._send_to_player(player_id, MessageType.PING, {
                "timestamp": message.data.get("timestamp", time.time())
            })
        
        elif message.type == MessageType.ADD_BOT:
            # Admin command to add bot
            import sys
            bot_name = message.data.get("name")
            print(f"*** ADD_BOT HANDLER CALLED ***", flush=True)
            print(f"Received ADD_BOT request for: {bot_name}", flush=True)
            sys.stdout.flush()
            bot_id = self.add_bot(bot_name)
            print(f"Bot added with ID: {bot_id}", flush=True)
            sys.stdout.flush()
            print(f"Current bot count: {len(self.bots)}, total players: {len(self.players)}", flush=True)
            sys.stdout.flush()
        
        elif message.type == MessageType.REMOVE_BOT:
            # Admin command to remove bot
            bot_id = message.data.get("bot_id")
            print(f"Received REMOVE_BOT request for: {bot_id}")
            self.remove_bot(bot_id)
        
        elif message.type == MessageType.START_GAME:
            # Request to start the game
            if not self.game_state.game_active:
                self._start_game()
            else:
                print("Game already active, ignoring START_GAME request")
    
    def _game_loop(self):
        """Main game update loop"""
        while self.running:
            now = time.time()
            dt = now - self.last_tick
            self.last_tick = now
            
            # Update bots
            with self.players_lock:
                for bot_id, bot in list(self.bots.items()):
                    bot.update(dt, self.game_state.boss_x, self.game_state.boss_y, 
                              self.boss_projectiles)
                    
                    # If bot is shooting, simulate boss damage
                    if bot.player.shooting and self.game_state.game_active:
                        self.game_state.boss_hp -= 5  # Base bot damage
            
            # Broadcast player states
            self._broadcast_player_states()
            
            # Check boss death
            if self.game_state.game_active and self.game_state.boss_hp <= 0:
                self._handle_boss_death()
            
            # Sleep to maintain tick rate
            sleep_time = (1.0 / self.tick_rate) - (time.time() - now)
            if sleep_time > 0:
                time.sleep(sleep_time)
    
    def _broadcast_player_states(self):
        """Broadcast all player states"""
        with self.players_lock:
            for player_id, player in self.players.items():
                self._broadcast(MessageType.PLAYER_STATE, {
                    "player_id": player_id,
                    "name": player.name,
                    "x": player.x,
                    "y": player.y,
                    "hp": player.hp,
                    "shooting": player.shooting,
                    "is_bot": player.is_bot
                }, exclude=player_id if not player.is_bot else None)
    
    def _check_game_start(self):
        """Check if game should start"""
        with self.players_lock:
            if len(self.players) < 1:
                return
            
            all_ready = all(p.ready for p in self.players.values())
            
            if all_ready and not self.game_state.game_active:
                self._start_game()
    
    def _start_game(self):
        """Start a new game"""
        self.game_state.game_active = True
        self.game_state.boss_hp = self.game_state.boss_max_hp
        self.game_state.start_time = time.time()
        
        self._broadcast(MessageType.GAME_START, {
            "level": self.game_state.level,
            "boss_hp": self.game_state.boss_hp
        })
        
        print(f"Game started - Level {self.game_state.level}")
    
    def _handle_boss_death(self):
        """Handle boss death"""
        self.game_state.game_active = False
        self.game_state.level += 1
        
        # Calculate new boss HP using scaling
        # Import here to avoid circular dependencies, and it works because
        # bootstrap ensures package root is in sys.path
        try:
            from game.scaling import ScalingFormulas
            self.game_state.boss_max_hp = ScalingFormulas.boss_hp(self.game_state.level)
        except (ImportError, AttributeError) as e:
            # Fallback scaling if import fails (shouldn't happen with bootstrap)
            print(f"Warning: Could not import ScalingFormulas, using fallback: {e}")
            self.game_state.boss_max_hp = 500 * (1.15 ** self.game_state.level)
        
        self.game_state.boss_hp = self.game_state.boss_max_hp
        
        self._broadcast(MessageType.GAME_END, {
            "victory": True,
            "level": self.game_state.level - 1,
            "next_level": self.game_state.level
        })
        
        # Reset ready states
        with self.players_lock:
            for player in self.players.values():
                player.ready = player.is_bot  # Bots stay ready
        
        print(f"Boss defeated! Advancing to level {self.game_state.level}")
    
    def _send_game_state(self, player_id: str):
        """Send current game state to a player"""
        with self.players_lock:
            players_info = [
                {
                    "player_id": pid,
                    "name": p.name,
                    "is_bot": p.is_bot,
                    "ready": p.ready
                }
                for pid, p in self.players.items()
            ]
        
        self._send_to_player(player_id, MessageType.GAME_STATE, {
            "level": self.game_state.level,
            "boss_hp": self.game_state.boss_hp,
            "boss_max_hp": self.game_state.boss_max_hp,
            "game_active": self.game_state.game_active,
            "players": players_info
        })
    
    def _send_to_player(self, player_id: str, msg_type: MessageType, data: Dict):
        """Send message to specific player"""
        with self.players_lock:
            player = self.players.get(player_id)
            if not player or not player.socket or player.is_bot:
                return
        
        try:
            message = NetworkMessage(msg_type, data, "server")
            encoded = serialize_message(message)
            
            player.socket.sendall(len(encoded).to_bytes(4, 'big'))
            player.socket.sendall(encoded)
        except Exception as e:
            print(f"Send error to {player_id}: {e}")
    
    def _broadcast(self, msg_type: MessageType, data: Dict, exclude: str = None):
        """Broadcast message to all players"""
        with self.players_lock:
            for player_id in list(self.players.keys()):
                if player_id != exclude:
                    self._send_to_player(player_id, msg_type, data)
    
    def _broadcast_lobby_update(self):
        """Broadcast lobby player list update to all players"""
        with self.players_lock:
            players_info = [
                {
                    "player_id": pid,
                    "name": p.name,
                    "is_bot": p.is_bot,
                    "ready": p.ready,
                    "is_host": False  # First player is host, could be enhanced
                }
                for pid, p in self.players.items()
            ]
            
            # Mark first non-bot player as host
            for player_info in players_info:
                if not player_info["is_bot"]:
                    player_info["is_host"] = True
                    break
        
        print(f"Broadcasting LOBBY_UPDATE with {len(players_info)} players")
        self._broadcast(MessageType.LOBBY_UPDATE, {
            "players": players_info
        })


def run_server(host: str = "0.0.0.0", port: int = 5555, bot_count: int = 0):
    """Run the game server with optional bots"""
    server = GameServer(host, port)
    
    if server.start():
        # Add bots if requested
        for i in range(bot_count):
            server.add_bot(f"TestBot_{i+1}")
        
        try:
            print("Server running. Press Ctrl+C to stop.")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        
        server.stop()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Cube Boss Fight Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host address")
    parser.add_argument("--port", type=int, default=5555, help="Port number")
    parser.add_argument("--bots", type=int, default=0, help="Number of bots to add")
    args = parser.parse_args()
    
    run_server(args.host, args.port, args.bots)

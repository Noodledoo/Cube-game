"""
FILE: network/client.py
Network client for multiplayer connectivity with offline fallback
"""

import socket
import threading
import time
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass

from protocol import (
    MessageType, NetworkMessage,
    serialize_message, deserialize_message
)


@dataclass
class ServerInfo:
    """Information about a discovered server"""
    address: str
    port: int
    name: str
    players: int
    max_players: int
    ping: float


class NetworkClient:
    """Network client for multiplayer game connection"""
    
    def __init__(self):
        self.socket: Optional[socket.socket] = None
        self.connected = False
        self.player_id: Optional[str] = None
        self.player_name = "Player"
        
        # Server info
        self.server_address = ""
        self.server_port = 5555
        
        # Message handlers
        self.message_handlers: Dict[MessageType, Callable] = {}
        
        # Receive thread
        self.receive_thread: Optional[threading.Thread] = None
        self.running = False
        
        # Game state cache
        self.game_state_cache: Dict[str, Any] = {}
        self.other_players: Dict[str, Dict] = {}
        self.latency = 0.0
        
        # Message queue for thread-safe access
        self.message_queue: List[NetworkMessage] = []
        self.queue_lock = threading.Lock()
    
    def register_handler(self, msg_type: MessageType, handler: Callable):
        """Register a handler for a specific message type"""
        self.message_handlers[msg_type] = handler
    
    def connect(self, address: str, port: int, player_name: str = "Player") -> bool:
        """Connect to a game server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5.0)
            self.socket.connect((address, port))
            self.socket.settimeout(None)
            
            self.server_address = address
            self.server_port = port
            self.player_name = player_name
            self.connected = True
            self.running = True
            
            # Start receive thread
            self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.receive_thread.start()
            
            # Send join request
            self.send(MessageType.PLAYER_JOIN, {"name": player_name})
            
            return True
            
        except socket.timeout:
            print(f"Connection timeout to {address}:{port}")
            return False
        except ConnectionRefusedError:
            print(f"Connection refused by {address}:{port}")
            return False
        except Exception as e:
            print(f"Connection error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from server"""
        if self.connected:
            self.running = False
            self.send(MessageType.PLAYER_LEAVE, {"player_id": self.player_id})
            
            if self.socket:
                try:
                    self.socket.close()
                except OSError:
                    pass
            
            self.connected = False
            self.socket = None
            self.player_id = None
            self.other_players.clear()
    
    def send(self, msg_type: MessageType, data: Dict[str, Any]) -> bool:
        """Send a message to the server"""
        if not self.connected or not self.socket:
            print(f"Client send failed: connected={self.connected}, socket={self.socket is not None}")
            return False
        
        try:
            message = NetworkMessage(msg_type, data, self.player_id or "")
            encoded = serialize_message(message)
            
            print(f"Client: Sending message type {msg_type.name}, size {len(encoded)} bytes")
            
            # Send length prefix then data
            length = len(encoded)
            self.socket.sendall(length.to_bytes(4, 'big'))
            self.socket.sendall(encoded)
            print(f"Client: Message sent successfully")
            return True
            
        except Exception as e:
            print(f"Send error: {e}")
            import traceback
            traceback.print_exc()
            self.disconnect()
            return False
    
    def send_player_state(self, x: float, y: float, hp: float, shooting: bool = False):
        """Send player state update"""
        self.send(MessageType.PLAYER_STATE, {
            "x": x,
            "y": y,
            "hp": hp,
            "shooting": shooting
        })
    
    def send_boss_hit(self, damage: float, projectile_id: str = ""):
        """Report boss damage to server"""
        self.send(MessageType.BOSS_HIT, {
            "damage": damage,
            "projectile_id": projectile_id
        })
    
    def send_chat(self, message: str):
        """Send chat message"""
        self.send(MessageType.CHAT, {"message": message})
    
    def send_ready(self, ready: bool = True):
        """Send ready status"""
        self.send(MessageType.READY, {"ready": ready})
    
    def _receive_loop(self):
        """Background thread to receive messages"""
        while self.running and self.socket:
            try:
                # Read length prefix
                length_data = self._recv_exact(4)
                if not length_data:
                    break
                
                length = int.from_bytes(length_data, 'big')
                if length > 1024 * 1024:  # Max 1MB message
                    print("Message too large, disconnecting")
                    break
                
                # Read message data
                message_data = self._recv_exact(length)
                if not message_data:
                    break
                
                # Deserialize and queue
                message = deserialize_message(message_data)
                if message:
                    with self.queue_lock:
                        self.message_queue.append(message)
                    
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"Receive error: {e}")
                break
        
        self.connected = False
    
    def _recv_exact(self, size: int) -> Optional[bytes]:
        """Receive exactly size bytes"""
        data = b''
        while len(data) < size:
            try:
                chunk = self.socket.recv(size - len(data))
                if not chunk:
                    return None
                data += chunk
            except OSError:
                return None
        return data
    
    def process_messages(self):
        """Process queued messages - call this from main thread"""
        with self.queue_lock:
            messages = self.message_queue[:]
            self.message_queue.clear()
        
        for message in messages:
            self._handle_message(message)
    
    def _handle_message(self, message: NetworkMessage):
        """Handle a received message"""
        # Handle system messages
        if message.type == MessageType.PLAYER_JOIN:
            if "player_id" in message.data:
                self.player_id = message.data["player_id"]
        
        elif message.type == MessageType.GAME_STATE:
            self.game_state_cache = message.data
        
        elif message.type == MessageType.PLAYER_STATE:
            player_id = message.data.get("player_id", message.sender_id)
            if player_id != self.player_id:
                self.other_players[player_id] = message.data
        
        elif message.type == MessageType.PLAYER_LEAVE:
            player_id = message.data.get("player_id", message.sender_id)
            if player_id in self.other_players:
                del self.other_players[player_id]
        
        elif message.type == MessageType.PING:
            # Calculate latency
            if "timestamp" in message.data:
                self.latency = (time.time() - message.data["timestamp"]) * 1000
        
        # Call registered handler
        if message.type in self.message_handlers:
            self.message_handlers[message.type](message)
    
    def get_other_players(self) -> Dict[str, Dict]:
        """Get dictionary of other players' states"""
        return self.other_players.copy()
    
    def ping(self):
        """Send ping to measure latency"""
        self.send(MessageType.PING, {"timestamp": time.time()})


class OfflineClient:
    """Offline client that mimics NetworkClient interface for singleplayer"""
    
    def __init__(self):
        self.connected = False
        self.player_id = "local_player"
        self.player_name = "Player"
        self.latency = 0.0
        self.other_players: Dict[str, Dict] = {}
        self.game_state_cache: Dict[str, Any] = {}
        self.message_handlers: Dict[MessageType, Callable] = {}
    
    def register_handler(self, msg_type: MessageType, handler: Callable):
        """Register handler (no-op for offline)"""
        self.message_handlers[msg_type] = handler
    
    def connect(self, address: str, port: int, player_name: str = "Player") -> bool:
        """Fake connection for offline play"""
        self.player_name = player_name
        self.connected = True
        return True
    
    def disconnect(self):
        """Disconnect from fake server"""
        self.connected = False
    
    def send(self, msg_type: MessageType, data: Dict[str, Any]) -> bool:
        """Send message (no-op for offline)"""
        return True
    
    def send_player_state(self, x: float, y: float, hp: float, shooting: bool = False):
        """Send player state (no-op for offline)"""
        pass
    
    def send_boss_hit(self, damage: float, projectile_id: str = ""):
        """Report boss damage (no-op for offline)"""
        pass
    
    def send_chat(self, message: str):
        """Send chat message (no-op for offline)"""
        pass
    
    def send_ready(self, ready: bool = True):
        """Send ready status (no-op for offline)"""
        pass
    
    def process_messages(self):
        """Process messages (no-op for offline)"""
        pass
    
    def get_other_players(self) -> Dict[str, Dict]:
        """Get other players (empty for offline)"""
        return {}
    
    def ping(self):
        """Ping (no-op for offline)"""
        pass

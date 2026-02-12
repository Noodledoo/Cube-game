"""
FILE: network/bot.py
Standalone bot AI for testing multiplayer
Can run as separate client connecting to server
"""

import socket
import threading
import time
import math
import random
import os
import sys
from typing import Dict, List, Optional
from dataclasses import dataclass

# Bootstrap: Ensure package root is in sys.path for IDE execution
_file_path = os.path.abspath(__file__)
_package_root = os.path.dirname(_file_path)
_package_root_resolved = os.path.normpath(_package_root)

# Add to sys.path if not already present (check normalized paths)
_sys_path_normalized = [os.path.normpath(p) for p in sys.path if p]
if _package_root_resolved not in _sys_path_normalized:
    sys.path.insert(0, _package_root_resolved)

from protocol import (
    MessageType, NetworkMessage,
    serialize_message, deserialize_message
)


@dataclass
class BotState:
    """Bot's internal state"""
    x: float = 400.0
    y: float = 300.0
    hp: float = 100.0
    max_hp: float = 100.0
    target_x: float = 400.0
    target_y: float = 300.0
    boss_x: float = 400.0
    boss_y: float = 300.0
    shooting: bool = False
    
    # Timers
    move_timer: float = 0.0
    shoot_timer: float = 0.0
    dodge_timer: float = 0.0


class StandaloneBot:
    """Bot client that connects to server as a player"""
    
    def __init__(self, name: str = "Bot"):
        self.name = name
        self.socket: Optional[socket.socket] = None
        self.connected = False
        self.running = False
        self.player_id: Optional[str] = None
        
        self.state = BotState()
        
        # Other players for reference
        self.other_players: Dict[str, Dict] = {}
        
        # Projectiles to dodge (from server updates)
        self.projectiles: List[Dict] = []
        
        # AI parameters
        self.aggression = random.uniform(0.3, 0.8)  # How often to shoot
        self.dodge_skill = random.uniform(0.5, 1.0)  # Dodge reaction speed
        self.move_speed = 200 + random.randint(-50, 50)
    
    def connect(self, address: str, port: int) -> bool:
        """Connect to game server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5.0)
            self.socket.connect((address, port))
            self.socket.settimeout(0.1)  # Non-blocking for game loop
            
            self.connected = True
            self.running = True
            
            # Send join
            self._send(MessageType.PLAYER_JOIN, {"name": self.name})
            
            return True
            
        except Exception as e:
            print(f"Bot connection failed: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from server"""
        self.running = False
        if self.socket:
            try:
                self._send(MessageType.PLAYER_LEAVE, {"player_id": self.player_id})
                self.socket.close()
            except OSError:
                pass
        self.connected = False
    
    def run(self):
        """Main bot loop"""
        last_time = time.time()
        update_rate = 1.0 / 30  # 30 updates per second
        
        while self.running:
            now = time.time()
            dt = now - last_time
            
            # Receive messages
            self._receive_messages()
            
            # Update AI
            self._update_ai(dt)
            
            # Send state update
            self._send(MessageType.PLAYER_STATE, {
                "x": self.state.x,
                "y": self.state.y,
                "hp": self.state.hp,
                "shooting": self.state.shooting
            })
            
            last_time = now
            
            # Sleep to maintain update rate
            sleep_time = update_rate - (time.time() - now)
            if sleep_time > 0:
                time.sleep(sleep_time)
    
    def _receive_messages(self):
        """Receive and process messages from server"""
        while True:
            try:
                # Read length
                length_data = self.socket.recv(4)
                if not length_data:
                    self.running = False
                    return
                
                length = int.from_bytes(length_data, 'big')
                if length > 1024 * 1024:
                    continue
                
                # Read message
                data = b''
                while len(data) < length:
                    chunk = self.socket.recv(length - len(data))
                    if not chunk:
                        self.running = False
                        return
                    data += chunk
                
                message = deserialize_message(data)
                if message:
                    self._handle_message(message)
                    
            except socket.timeout:
                break
            except Exception as e:
                if self.running:
                    print(f"Bot receive error: {e}")
                break
    
    def _handle_message(self, message: NetworkMessage):
        """Handle incoming message"""
        if message.type == MessageType.PLAYER_JOIN:
            if "player_id" in message.data:
                self.player_id = message.data["player_id"]
                print(f"Bot '{self.name}' assigned ID: {self.player_id}")
        
        elif message.type == MessageType.PLAYER_STATE:
            player_id = message.data.get("player_id")
            if player_id and player_id != self.player_id:
                self.other_players[player_id] = message.data
        
        elif message.type == MessageType.BOSS_STATE:
            self.state.boss_x = message.data.get("x", self.state.boss_x)
            self.state.boss_y = message.data.get("y", self.state.boss_y)
        
        elif message.type == MessageType.GAME_START:
            print(f"Bot '{self.name}': Game started!")
            self._send(MessageType.READY, {"ready": True})
        
        elif message.type == MessageType.GAME_END:
            if message.data.get("victory"):
                print(f"Bot '{self.name}': Victory!")
            else:
                print(f"Bot '{self.name}': Defeat!")
            self._send(MessageType.READY, {"ready": True})
        
        elif message.type == MessageType.GAME_STATE:
            # Initial game state received
            print(f"Bot '{self.name}': Received game state, sending ready")
            self._send(MessageType.READY, {"ready": True})
    
    def _update_ai(self, dt: float):
        """Update bot AI behavior"""
        self.state.move_timer -= dt
        self.state.shoot_timer -= dt
        self.state.dodge_timer -= dt
        
        # Dodge projectiles (simplified - would need actual projectile data)
        if self.state.dodge_timer <= 0 and random.random() < 0.1 * self.dodge_skill:
            # Random dodge movement
            dodge_angle = random.uniform(0, 2 * math.pi)
            self.state.x += math.cos(dodge_angle) * 50
            self.state.y += math.sin(dodge_angle) * 50
            self.state.dodge_timer = 0.5
        
        # Movement toward target
        if self.state.move_timer <= 0:
            # Pick new target - bias toward boss area
            if random.random() < 0.3:
                # Move toward boss
                self.state.target_x = self.state.boss_x + random.randint(-100, 100)
                self.state.target_y = self.state.boss_y + random.randint(-100, 100)
            else:
                # Random movement
                self.state.target_x = random.randint(100, 700)
                self.state.target_y = random.randint(100, 500)
            self.state.move_timer = random.uniform(1.0, 3.0)
        
        # Move toward target
        dx = self.state.target_x - self.state.x
        dy = self.state.target_y - self.state.y
        dist = math.hypot(dx, dy)
        
        if dist > 10:
            speed = self.move_speed * dt
            self.state.x += (dx / dist) * speed
            self.state.y += (dy / dist) * speed
        
        # Keep in bounds
        self.state.x = max(30, min(770, self.state.x))
        self.state.y = max(30, min(570, self.state.y))
        
        # Shooting behavior
        if self.state.shoot_timer <= 0:
            self.state.shooting = random.random() < self.aggression
            if self.state.shooting:
                # Simulate boss hit
                self._send(MessageType.BOSS_HIT, {"damage": 5})
            self.state.shoot_timer = random.uniform(0.2, 0.6)
        else:
            self.state.shooting = False
    
    def _send(self, msg_type: MessageType, data: Dict):
        """Send message to server"""
        if not self.connected or not self.socket:
            return
        
        try:
            message = NetworkMessage(msg_type, data, self.player_id or "")
            encoded = serialize_message(message)
            
            self.socket.sendall(len(encoded).to_bytes(4, 'big'))
            self.socket.sendall(encoded)
        except Exception as e:
            print(f"Bot send error: {e}")
            self.running = False


def run_bot(address: str, port: int, name: str = "TestBot"):
    """Run a standalone bot"""
    bot = StandaloneBot(name)
    
    if bot.connect(address, port):
        print(f"Bot '{name}' connected to {address}:{port}")
        
        try:
            bot.run()
        except KeyboardInterrupt:
            pass
        
        bot.disconnect()
        print(f"Bot '{name}' disconnected")
    else:
        print(f"Bot '{name}' failed to connect")


def run_bot_swarm(address: str, port: int, count: int = 4, name_prefix: str = "Bot"):
    """Run multiple bots in parallel"""
    bots: List[StandaloneBot] = []
    threads: List[threading.Thread] = []
    
    for i in range(count):
        name = f"{name_prefix}_{i+1}"
        bot = StandaloneBot(name)
        
        if bot.connect(address, port):
            bots.append(bot)
            thread = threading.Thread(target=bot.run, daemon=True)
            thread.start()
            threads.append(thread)
            print(f"Bot '{name}' started")
            time.sleep(0.1)  # Stagger connections
    
    if bots:
        try:
            print(f"Running {len(bots)} bots. Press Ctrl+C to stop.")
            while any(t.is_alive() for t in threads):
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        
        for bot in bots:
            bot.disconnect()
        
        print("All bots stopped")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Cube Boss Fight Bot Client")
    parser.add_argument("--host", default="127.0.0.1", help="Server address")
    parser.add_argument("--port", type=int, default=5555, help="Server port")
    parser.add_argument("--name", default="TestBot", help="Bot name")
    parser.add_argument("--count", type=int, default=1, help="Number of bots to run")
    args = parser.parse_args()
    
    if args.count > 1:
        run_bot_swarm(args.host, args.port, args.count, args.name)
    else:
        run_bot(args.host, args.port, args.name)

"""
FILE: network/protocol.py
Network protocol definitions, message types, and serialization
"""

import json
import time
from enum import Enum, auto
from dataclasses import dataclass
from typing import Dict, Any, Optional


class MessageType(Enum):
    """Network message types"""
    # Connection
    CONNECT = auto()
    DISCONNECT = auto()
    PING = auto()
    PONG = auto()
    
    # Player management
    PLAYER_JOIN = auto()
    PLAYER_LEAVE = auto()
    PLAYER_STATE = auto()
    PLAYER_READY = auto()
    READY = auto()
    
    # Lobby
    JOIN_LOBBY = auto()
    LEAVE_LOBBY = auto()
    LOBBY_UPDATE = auto()
    START_GAME = auto()
    GAME_START = auto()
    GAME_END = auto()
    
    # Game state
    GAME_STATE = auto()
    PLAYER_INPUT = auto()
    PLAYER_POSITION = auto()
    PLAYER_SHOOT = auto()
    PLAYER_ABILITY = auto()
    
    # Boss state
    BOSS_UPDATE = auto()
    BOSS_STATE = auto()
    BOSS_ATTACK = auto()
    BOSS_HIT = auto()
    PROJECTILE_SPAWN = auto()
    PROJECTILE_DESTROY = auto()
    
    # Events
    PLAYER_HIT = auto()
    PLAYER_DIED = auto()
    BOSS_DIED = auto()
    LEVEL_COMPLETE = auto()
    
    # Chat
    CHAT_MESSAGE = auto()
    CHAT = auto()
    
    # Admin
    ADMIN_COMMAND = auto()
    ADD_BOT = auto()
    REMOVE_BOT = auto()


@dataclass
class NetworkMessage:
    """Network message container"""
    type: MessageType
    data: Dict[str, Any]
    sender_id: str = ""
    timestamp: float = 0.0
    
    def __post_init__(self):
        """Auto-set timestamp if not provided"""
        if self.timestamp == 0.0:
            self.timestamp = time.time()
    
    def to_bytes(self) -> bytes:
        """Serialize message to bytes"""
        payload = {
            "type": self.type.name,
            "data": self.data,
            "sender_id": self.sender_id,
            "timestamp": self.timestamp
        }
        return json.dumps(payload).encode('utf-8')
    
    @classmethod
    def from_bytes(cls, data: bytes) -> Optional['NetworkMessage']:
        """Deserialize message from bytes"""
        try:
            payload = json.loads(data.decode('utf-8'))
            msg_type = MessageType[payload["type"]]
            return cls(
                type=msg_type,
                data=payload.get("data", {}),
                sender_id=payload.get("sender_id", ""),
                timestamp=payload.get("timestamp", 0.0)
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Message deserialization error: {e}")
            print(f"Failed data: {data[:200] if len(data) > 200 else data}")
            import traceback
            traceback.print_exc()
            return None


def serialize_message(message: NetworkMessage) -> bytes:
    """Serialize a NetworkMessage to bytes for transmission"""
    return message.to_bytes()


def deserialize_message(data: bytes) -> Optional[NetworkMessage]:
    """Deserialize bytes to a NetworkMessage"""
    return NetworkMessage.from_bytes(data)


def create_connect_message(player_name: str) -> NetworkMessage:
    """Create connection request message"""
    return NetworkMessage(
        type=MessageType.CONNECT,
        data={"name": player_name}
    )


def create_player_join_message(player_name: str, player_id: str = "") -> NetworkMessage:
    """Create player join message"""
    return NetworkMessage(
        type=MessageType.PLAYER_JOIN,
        data={"name": player_name, "player_id": player_id}
    )


def create_player_leave_message(player_id: str, name: str = "") -> NetworkMessage:
    """Create player leave message"""
    return NetworkMessage(
        type=MessageType.PLAYER_LEAVE,
        data={"player_id": player_id, "name": name}
    )


def create_player_state_message(x: float, y: float, hp: float, 
                                shooting: bool = False, player_id: str = "") -> NetworkMessage:
    """Create player state update message"""
    return NetworkMessage(
        type=MessageType.PLAYER_STATE,
        data={"x": x, "y": y, "hp": hp, "shooting": shooting, "player_id": player_id},
        sender_id=player_id
    )


def create_player_position_message(x: float, y: float, player_id: str = "") -> NetworkMessage:
    """Create player position update message"""
    return NetworkMessage(
        type=MessageType.PLAYER_POSITION,
        data={"x": x, "y": y},
        sender_id=player_id
    )


def create_player_shoot_message(x: float, y: float, angle: float, 
                                damage: float, player_id: str = "") -> NetworkMessage:
    """Create player shoot message"""
    return NetworkMessage(
        type=MessageType.PLAYER_SHOOT,
        data={"x": x, "y": y, "angle": angle, "damage": damage},
        sender_id=player_id
    )


def create_boss_update_message(x: float, y: float, hp: float, 
                               emotion: str, charging: bool) -> NetworkMessage:
    """Create boss state update message"""
    return NetworkMessage(
        type=MessageType.BOSS_UPDATE,
        data={
            "x": x, "y": y, "hp": hp,
            "emotion": emotion, "charging": charging
        }
    )


def create_boss_state_message(x: float, y: float, hp: float, max_hp: float) -> NetworkMessage:
    """Create boss state message"""
    return NetworkMessage(
        type=MessageType.BOSS_STATE,
        data={"x": x, "y": y, "hp": hp, "max_hp": max_hp}
    )


def create_boss_hit_message(damage: float, projectile_id: str = "") -> NetworkMessage:
    """Create boss hit message"""
    return NetworkMessage(
        type=MessageType.BOSS_HIT,
        data={"damage": damage, "projectile_id": projectile_id}
    )


def create_chat_message(sender_name: str, message: str) -> NetworkMessage:
    """Create chat message"""
    return NetworkMessage(
        type=MessageType.CHAT_MESSAGE,
        data={"sender": sender_name, "message": message}
    )


def create_lobby_update_message(players: list) -> NetworkMessage:
    """Create lobby player list update"""
    return NetworkMessage(
        type=MessageType.LOBBY_UPDATE,
        data={"players": players}
    )


def create_game_start_message(level: int, boss_hp: float) -> NetworkMessage:
    """Create game start message"""
    return NetworkMessage(
        type=MessageType.GAME_START,
        data={"level": level, "boss_hp": boss_hp}
    )


def create_game_end_message(victory: bool, level: int, next_level: int = 0) -> NetworkMessage:
    """Create game end message"""
    return NetworkMessage(
        type=MessageType.GAME_END,
        data={"victory": victory, "level": level, "next_level": next_level}
    )


def create_game_state_message(level: int, boss_hp: float, boss_max_hp: float,
                              game_active: bool, players: list) -> NetworkMessage:
    """Create full game state message"""
    return NetworkMessage(
        type=MessageType.GAME_STATE,
        data={
            "level": level,
            "boss_hp": boss_hp,
            "boss_max_hp": boss_max_hp,
            "game_active": game_active,
            "players": players
        }
    )


def create_ready_message(ready: bool) -> NetworkMessage:
    """Create ready status message"""
    return NetworkMessage(
        type=MessageType.READY,
        data={"ready": ready}
    )


def create_ping_message() -> NetworkMessage:
    """Create ping message with timestamp"""
    return NetworkMessage(
        type=MessageType.PING,
        data={"timestamp": time.time()}
    )

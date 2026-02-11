"""
FILE: core/constants.py
Game constants and enumerations
"""

from enum import Enum, auto

class GameMode(Enum):
    """Game mode types"""
    SINGLEPLAYER = auto()
    MULTIPLAYER = auto()
    MULTIPLAYER_HOST = auto()
    MULTIPLAYER_CLIENT = auto()
    MULTIPLAYER_COOP = auto()
    PVP = auto()  # Player vs Player mode

class SessionState(Enum):
    """Multiplayer session states"""
    MENU = auto()
    DISCONNECTED = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    IN_LOBBY = auto()
    IN_GAME = auto()
    RECONNECTING = auto()

# Screen dimensions
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600

# Network constants
DEFAULT_PORT = 5555
MAX_PLAYERS = 4
TICK_RATE = 60
NET_TIMEOUT = 5.0

# Game constants
PLAYER_RADIUS = 15
BOSS_RADIUS = 60
PROJECTILE_RADIUS = 8

# Colors
COLORS = {
    "player": (0, 255, 0),
    "player_low_hp": (255, 255, 0),
    "player_critical": (255, 0, 0),
    "boss": (70, 180, 255),
    "boss_charging": (255, 120, 0),
    "boss_super": (255, 0, 255),
    "laser": (255, 60, 60),
    "homing": (255, 150, 0),
    "spiral": (150, 100, 255),
}

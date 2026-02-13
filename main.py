"""
FILE: main.py
Complete main entry point with singleplayer and multiplayer support
Preserves ALL existing functionality while adding network features
"""

import pygame
import sys
import time
import math
import argparse
import os

# Bootstrap: Ensure package root is in sys.path for IDE execution
_file_path = os.path.abspath(__file__)
_package_root = os.path.dirname(_file_path)  # Directory containing main.py (cube_boss_fight/)
_package_root_resolved = os.path.normpath(_package_root)

# Add to sys.path if not already present (check normalized paths)
_sys_path_normalized = [os.path.normpath(p) for p in sys.path if p]
if _package_root_resolved not in _sys_path_normalized:
    sys.path.insert(0, _package_root_resolved)

from states import GameState, PlayerState, BossState, AdminState
from admin_console import AdminConsole
from abilities import AbilityManager, Ability
from animations import AnimationManager
from rendering import Renderer
from boss_ai import BossAI
from player import Player
from ui import UIManager
from scaling import ScalingFormulas

from config import (load_save, save_progress, reset_save, SCREEN_WIDTH, SCREEN_HEIGHT,
                    load_multiplayer_save, save_multiplayer_progress, update_multiplayer_stats)
from constants import GameMode, SessionState

from client import NetworkClient, OfflineClient
from server import GameServer
from protocol import MessageType


class Game:
    """Main game controller with complete feature integration and multiplayer support"""

    @property
    def is_multiplayer_mode(self):
        return self.mode in (GameMode.MULTIPLAYER, GameMode.MULTIPLAYER_COOP, GameMode.PVP)

    def __init__(self, mode: GameMode = GameMode.SINGLEPLAYER,
                 host_server: bool = False, server_address: str = "127.0.0.1",
                 server_port: int = 5555):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Cube Boss Fight - Ultimate Edition")
        self.clock = pygame.time.Clock()
        
        # Game mode
        self.mode = mode
        self.session_state = SessionState.MENU
        
        # Load appropriate save data based on mode
        if self.is_multiplayer_mode:
            self.save_data = load_multiplayer_save()
        else:
            self.save_data = load_save()
        
        # Multiplayer session tracking
        self.mp_session_damage = 0.0
        self.mp_session_start_time = 0.0
        
        # Initialize state
        self.game_state = GameState()
        self.game_state.level = 1
        self.game_state.coins = self.save_data["coins"]
        self.game_state.max_level = self.save_data["max_level"]
        
        self.player_state = PlayerState()
        self.boss_state = BossState()
        self.admin_state = AdminState()
        
        # Initialize managers
        self.console = AdminConsole()
        self.ability_manager = AbilityManager()
        self.animation_manager = AnimationManager()
        self.renderer = Renderer(self.screen)
        self.ui_manager = UIManager(self.screen, self.save_data)
        
        # Initialize game systems
        self.boss_ai = BossAI(self.boss_state, self.animation_manager)
        self.player = Player(self.player_state, self.save_data, self.ability_manager, self.animation_manager)
        
        # Network components
        self.network_client = None
        self.game_server = None
        self.server_address = server_address
        self.server_port = server_port
        
        # Host server if requested
        if host_server and self.is_multiplayer_mode:
            self._start_server()

        # Setup network client based on mode
        if self.is_multiplayer_mode:
            self.network_client = NetworkClient()
            self._setup_network_handlers()
        else:
            self.network_client = OfflineClient()
        
        # Register abilities
        self._register_abilities()

        # Restore ability stacks from save_data
        for ability_name, stacks in self.save_data.get("abilities", {}).items():
            if stacks > 0 and ability_name in self.ability_manager.registry:
                reg = self.ability_manager.registry[ability_name]
                ab = Ability(
                    name=reg.name, description=reg.description,
                    rarity=reg.rarity, cooldown=reg.cooldown,
                    key=reg.key, stacks=stacks, max_stacks=reg.max_stacks
                )
                self.ability_manager.player_abilities[ability_name] = ab
                self.ability_manager.last_used[ability_name] = -999.0

        # Set console callback with save_data reference
        self.console.set_execute_callback(self._execute_console_command)
        self.console.set_save_data(self.save_data)
        
        # Time freeze tracking
        self.time_freeze_active = False
        self.time_freeze_end = 0
        
        # Multiplayer state
        self.other_players = {}
        self.player_projectiles_remote = {}
        
        self.running = True
        self.secret_code = ""
        self.secret_code_target = "wwssadadba"
    
    def _start_server(self):
        """Start local game server"""
        self.game_server = GameServer(port=self.server_port)
        if self.game_server.start():
            print(f"Server started on port {self.server_port}")
        else:
            print("Failed to start server")
            self.game_server = None
    
    def _setup_network_handlers(self):
        """Setup handlers for network messages"""
        self.network_client.register_handler(MessageType.PLAYER_STATE, self._on_player_state)
        self.network_client.register_handler(MessageType.BOSS_STATE, self._on_boss_state)
        self.network_client.register_handler(MessageType.GAME_START, self._on_game_start)
        self.network_client.register_handler(MessageType.GAME_END, self._on_game_end)
        self.network_client.register_handler(MessageType.CHAT, self._on_chat)
        self.network_client.register_handler(MessageType.PLAYER_JOIN, self._on_player_join)
        self.network_client.register_handler(MessageType.PLAYER_LEAVE, self._on_player_leave)
        self.network_client.register_handler(MessageType.GAME_STATE, self._on_game_state)
        self.network_client.register_handler(MessageType.LOBBY_UPDATE, self._on_lobby_update)
    
    def _on_player_state(self, message):
        """Handle player state update from server"""
        player_id = message.data.get("player_id")
        if player_id and player_id != self.network_client.player_id:
            self.other_players[player_id] = message.data
    
    def _on_boss_state(self, message):
        """Handle boss state update from server"""
        self.boss_state.hp = message.data.get("hp", self.boss_state.hp)
        self.boss_state.max_hp = message.data.get("max_hp", self.boss_state.max_hp)
        self.boss_state.x = message.data.get("x", self.boss_state.x)
        self.boss_state.y = message.data.get("y", self.boss_state.y)
    
    def _on_game_start(self, message):
        """Handle game start from server"""
        level = message.data.get("level", 1)
        self.start_level(level)
    
    def _on_game_end(self, message):
        """Handle game end from server"""
        if message.data.get("victory"):
            self._handle_victory()
        else:
            self.game_state.screen_state = "GAMEOVER"
    
    def _on_chat(self, message):
        """Handle chat message from server"""
        sender = message.data.get("sender", "Unknown")
        msg = message.data.get("message", "")
        self.ui_manager.add_chat_message(sender, msg)
    
    def _on_player_join(self, message):
        """Handle player join"""
        sender = message.data.get("name", "Player")
        self.ui_manager.add_chat_message("System", f"{sender} joined the game")
        
    def _on_player_leave(self, message):
        """Handle player leave"""
        sender = message.data.get("name", "Player")
        self.ui_manager.add_chat_message("System", f"{sender} left the game")
    
    def _on_game_state(self, message):
        """Handle game state update from server (includes lobby player list)"""
        if "players" in message.data:
            players = message.data["players"]
            print(f"Received GAME_STATE with {len(players)} players")
            # Update lobby player list
            self.ui_manager.set_lobby_players(players)
    
    def _on_lobby_update(self, message):
        """Handle lobby update from server"""
        if "players" in message.data:
            players = message.data["players"]
            print(f"Received LOBBY_UPDATE with {len(players)} players")
            # Update lobby player list
            self.ui_manager.set_lobby_players(players)
    
    def add_bot(self, name: str = None) -> str:
        """Add a bot to the server"""
        if self.game_server:
            return self.game_server.add_bot(name)
        return ""
    
    def remove_bot(self, player_id: str) -> bool:
        """Remove a bot from the server"""
        if self.game_server:
            return self.game_server.remove_bot(player_id)
        return False
    
    def get_bot_count(self) -> int:
        """Get number of bots on the server"""
        if self.game_server:
            return self.game_server.get_bot_count()
        return 0
    
    def _register_abilities(self):
        """Register all game abilities"""
        abilities = [
            Ability("teleport", "Teleport to opposite side", "common", 8.0, pygame.K_e),
            Ability("dash", "Quick dash away from boss", "common", 5.0, pygame.K_q),
            Ability("timeshatter", "Freeze enemies for 2s", "rare", 14.0, pygame.K_r),
            Ability("shockwave", "Push bullets away", "rare", 10.0, pygame.K_f),
            Ability("chaos_bargain", "+Damage, -MaxHP", "rare", 0.0, None),
            Ability("chronoking", "Permanent slow aura", "legendary", 0.0, None),
            Ability("singularity", "Bullets curve away", "legendary", 0.0, None),
        ]
        
        for ability in abilities:
            self.ability_manager.register_ability(ability)
    
    def _execute_console_command(self, command):
        """Execute console command"""
        # Enforce admin permission
        if not self.save_data["settings"]["admin"]:
            return "Error: Admin mode required. Enable in Settings."
            
        parts = command.strip().split()
        if not parts:
            return "No command"
        
        cmd = parts[0].lower()
        
        # Bot commands
        if cmd == "addbot":
            # Check if we're in multiplayer mode (any multiplayer mode)
            is_multiplayer = self.mode in [GameMode.MULTIPLAYER, GameMode.MULTIPLAYER_COOP, GameMode.PVP]
            if is_multiplayer and self.network_client and isinstance(self.network_client, NetworkClient):
                name = parts[1] if len(parts) > 1 else None
                print(f"Console: Sending ADD_BOT request with name: {name}")
                print(f"Console: NetworkClient connected: {self.network_client.connected}, socket: {self.network_client.socket is not None}")
                print(f"Console: MessageType.ADD_BOT = {MessageType.ADD_BOT}")
                result = self.network_client.send(MessageType.ADD_BOT, {"name": name})
                print(f"Console: Send result: {result}")
                if result:
                    return f"Request sent to add bot: {name or 'default'}"
                else:
                    return "Failed to send bot request - not connected"
            elif self.game_server:
                name = parts[1] if len(parts) > 1 else None
                print(f"Console: Adding bot locally with name: {name}")
                bot_id = self.add_bot(name)
                return f"Bot added locally: {bot_id}"
            return "Error: Must be in multiplayer mode or hosting"
        
        elif cmd == "removebot":
            if self.is_multiplayer_mode and isinstance(self.network_client, NetworkClient) and self.network_client.connected:
                bot_id = parts[1] if len(parts) > 1 else None
                self.network_client.send(MessageType.REMOVE_BOT, {"bot_id": bot_id})
                return "Request sent to remove bot"
            elif self.game_server:
                if len(parts) < 2:
                    return "Usage: removebot <player_id>"
                if self.remove_bot(parts[1]):
                    return f"Bot removed: {parts[1]}"
                return "Failed to remove bot"
            return "Error: Must be in multiplayer mode or hosting"
        
        elif cmd == "botcount":
            if self.is_multiplayer_mode and isinstance(self.network_client, NetworkClient):
                # Count bots in other_players + own server knowledge if hosting
                count = 0
                for data in self.other_players.values():
                    if data.get("is_bot"):
                        count += 1
                return f"Bots: {count} (visible)"
            elif self.game_server:
                return f"Bot count: {self.get_bot_count()}"
            return "Server not running"
        
        elif cmd == "listbots":
            if self.is_multiplayer_mode:
                bots = []
                for pid, data in self.other_players.items():
                    if data.get("is_bot"):
                        bots.append(f"{data.get('name')} ({pid})")
                
                if self.game_server:
                    # If hosting, we can see strict server truth too
                    server_bots = [f"{p.name} ({p.player_id})" for p in self.game_server.players.values() if p.is_bot]
                    return f"Server Bots: {', '.join(server_bots)}"
                
                if not bots:
                    return "No visible bots"
                return "Bots:\n" + "\n".join(bots)
            return "Server not running"
        
        # Standard admin commands
        return self.admin_state.execute_command(
            command,
            self.game_state,
            self.player_state,
            self.boss_state,
            self.save_data,
            self.ability_manager
        )
    
    def handle_events(self):
        """Handle all input events"""
        events = pygame.event.get()
        
        for event in events:
            if event.type == pygame.QUIT:
                save_progress(self.save_data)
                self._cleanup_network()
                self.running = False
                return
            
            # Console toggle
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_BACKQUOTE:
                    self.console.visible = not self.console.visible
                
                # Pause toggle in game
                if event.key == pygame.K_ESCAPE and self.game_state.screen_state == "GAME":
                    self.game_state.paused = not self.game_state.paused
                
                # Parry
                if event.key == pygame.K_SPACE and self.game_state.screen_state == "GAME" and not self.game_state.paused:
                    self.player.activate_parry()
                
                # Secret code (when paused)
                if self.game_state.paused and self.game_state.screen_state == "GAME":
                    key_map = {
                        pygame.K_w: 'w', pygame.K_a: 'a',
                        pygame.K_s: 's', pygame.K_d: 'd',
                        pygame.K_b: 'b'
                    }
                    if event.key in key_map:
                        self.secret_code += key_map[event.key]
                        if len(self.secret_code) > 10:
                            self.secret_code = self.secret_code[-10:]
                        if self.secret_code == self.secret_code_target:
                            self.boss_state.hp = 0
                            self.game_state.paused = False
                            self.secret_code = ""
            
            # Let console handle events first
            if self.console.handle_event(event):
                continue
            
            # Let UI manager handle events
            action = self.ui_manager.handle_event(event, self.game_state, self.player_state, 
                                                  self.boss_state, self.ability_manager, self.save_data)
            
            if action:
                self._handle_ui_action(action)
    
    def _cleanup_network(self):
        """Cleanup network resources"""
        if self.network_client and self.network_client.connected:
            self.network_client.disconnect()
        
        if self.game_server:
            self.game_server.stop()
    
    def _handle_ui_action(self, action):
        """Handle UI actions"""
        if not action:
            return
            
        action_type = action.get("type")
        
        if action_type == "start_level":
            level = action["level"]
            self.start_level(level)
        
        elif action_type == "change_state":
            new_state = action["state"]
            self.game_state.screen_state = new_state
            self.game_state.paused = False
            
            # Handle mode changes for multiplayer
            if "mode" in action:
                if action["mode"] == "coop":
                    self.mode = GameMode.MULTIPLAYER_COOP
                elif action["mode"] == "pvp":
                    self.mode = GameMode.PVP
        
        elif action_type == "resume":
            self.game_state.paused = False
        
        elif action_type == "reset_save":
            self.save_data = reset_save()
            self.game_state.coins = 0
            self.game_state.max_level = 1
            self.ui_manager.save_data = self.save_data
            self.player.save_data = self.save_data
        
        elif action_type == "enter_temple":
            self.ability_manager.roll_temple_choices(3)
            self.ability_manager.reset_temple_session()
            self.game_state.screen_state = "ABILITY_TEMPLE"
        
        elif action_type == "select_ability":
            ability = action["ability"]
            self.ability_manager.select_ability(ability)
            self.save_data["ability_picks_used"] += 1
            # Sync ability stacks to save_data so game code can read them
            for name, ab in self.ability_manager.player_abilities.items():
                self.save_data["abilities"][name] = ab.stacks
            save_progress(self.save_data)
        
        elif action_type == "roll_temple":
            cost = self.ability_manager.get_roll_cost()
            if cost == 0 or self.game_state.coins >= cost:
                self.game_state.coins -= cost
                self.save_data["coins"] = self.game_state.coins
                self.ability_manager.increment_roll_count()
                self.ability_manager.roll_temple_choices(3)
                save_progress(self.save_data)
        
        elif action_type == "leave_temple":
            self.ability_manager.reset_temple_session()
            self.game_state.screen_state = "MENU"
        
        elif action_type == "buy_upgrade":
            key = action["key"]
            cost = action["cost"]
            current = action["current"]
            
            self.game_state.coins -= cost
            self.save_data["coins"] = self.game_state.coins
            
            if isinstance(current, bool):
                self.save_data["upgrades"][key] = True
            else:
                self.save_data["upgrades"][key] = current + 1
            
            save_progress(self.save_data)
        
        elif action_type == "toggle_theme":
            current = self.save_data["settings"]["theme"]
            self.save_data["settings"]["theme"] = "light" if current == "dark" else "dark"
            save_progress(self.save_data)
        
        elif action_type == "toggle_movement":
            current = self.save_data["settings"]["movement"]
            self.save_data["settings"]["movement"] = "arrows" if current == "mouse" else "mouse"
            save_progress(self.save_data)
        
        elif action_type == "toggle_colorblind":
            self.save_data["settings"]["colorblind"] = not self.save_data["settings"]["colorblind"]
            save_progress(self.save_data)
        
        # Multiplayer actions
        elif action_type == "connect_to_server":
            ip = action.get("ip", "127.0.0.1")
            port = action.get("port", 5555)
            name = action.get("name") or self.ui_manager.player_name_input or "Player"
            mode = action.get("mode", "coop")  # coop or pvp
            
            # Create NetworkClient if we don't have one or if it's OfflineClient
            if not isinstance(self.network_client, NetworkClient):
                self.network_client = NetworkClient()
                self._setup_network_handlers()

            if self.network_client.connect(ip, port, name):
                self.ui_manager.set_connection_status("connected")
                # Set mode based on action
                if mode == "pvp":
                    self.mode = GameMode.PVP
                else:
                    self.mode = GameMode.MULTIPLAYER_COOP
            else:
                self.ui_manager.set_connection_status("error", "Connection failed")

        elif action_type == "disconnect":
            if self.network_client:
                self.network_client.disconnect()
            # Switch back to OfflineClient
            self.network_client = OfflineClient()
            self.ui_manager.set_connection_status("disconnected")
            self.mode = GameMode.SINGLEPLAYER
        
        elif action_type == "send_chat":
            message = action.get("message", "")
            if self.network_client and isinstance(self.network_client, NetworkClient) and self.network_client.connected:
                self.network_client.send_chat(message)
        
        elif action_type == "host_game":
            port = action.get("port", 5555)
            name = action.get("name") or self.ui_manager.player_name_input or "Player"
            mode = action.get("mode", "coop")  # coop or pvp
            
            if not self.game_server:
                self.server_port = port
                self._start_server()
                if self.game_server:
                    # Create NetworkClient if we don't have one or if it's OfflineClient
                    if not isinstance(self.network_client, NetworkClient):
                        self.network_client = NetworkClient()
                        self._setup_network_handlers()

                    # Connect to own server
                    if self.network_client.connect("127.0.0.1", port, name):
                        self.ui_manager.set_connection_status("hosting")
                        # Set mode based on action
                        if mode == "pvp":
                            self.mode = GameMode.PVP
                        else:
                            self.mode = GameMode.MULTIPLAYER_COOP
                    else:
                        self.ui_manager.set_connection_status("error", "Failed to connect to local server")
                else:
                    print("Failed to start server")
            else:
                print("Server already running")
        
        elif action_type == "ready":
            if self.network_client and isinstance(self.network_client, NetworkClient) and self.network_client.connected:
                self.network_client.send(MessageType.READY, {"ready": True})
        
        elif action_type == "start_multiplayer_game":
            # Start the game if hosting
            if self.game_server:
                # Manually trigger game start (host can start even if not all ready)
                if not self.game_server.game_state.game_active:
                    # Start the game
                    self.game_server.game_state.game_active = True
                    self.game_server.game_state.boss_hp = self.game_server.game_state.boss_max_hp
                    self.game_server.game_state.start_time = time.time()
                    
                    self.game_server._broadcast(MessageType.GAME_START, {
                        "level": self.game_server.game_state.level,
                        "boss_hp": self.game_server.game_state.boss_hp
                    })
                    
                    # Start the level locally
                    self.start_level(self.game_server.game_state.level)
                    print("Multiplayer game started")
                else:
                    print("Game already active")
            elif self.network_client and isinstance(self.network_client, NetworkClient) and self.network_client.connected:
                # If not hosting, send START_GAME request to server
                self.network_client.send(MessageType.START_GAME, {})
                print("Sent start game request to server")
            else:
                print("Cannot start game - not connected")
    
    def start_level(self, level):
        """Start a specific level"""
        self.game_state.level = level
        self.game_state.screen_state = "GAME"
        self.game_state.paused = False
        
        # Reset boss
        self.boss_state.x = 400.0
        self.boss_state.y = 300.0
        self.boss_state.max_hp = ScalingFormulas.boss_hp(level)
        if level % 10 == 0:
            self.boss_state.max_hp *= 2
        self.boss_state.hp = self.boss_state.max_hp
        self.boss_state.charging = False
        self.boss_state.returning_to_center = False
        self.boss_state.emotion = "normal"
        
        # Reset player
        self.player_state.x = 200.0
        self.player_state.y = 300.0
        hp_bonus = (self.save_data["upgrades"]["health"] - 1) * 25
        golden_bonus = (self.save_data["upgrades"]["goldenheart"] - 1) * 50
        
        # Get chaos penalty safely
        chaos_penalty = 0
        if "abilities" in self.save_data:
            chaos_penalty = self.save_data["abilities"].get("chaos_bargain", 0) * 5
        
        self.player_state.max_hp = 100 + hp_bonus + golden_bonus - chaos_penalty
        
        # Apply godmode if owned
        if self.save_data["upgrades"]["godmode"] and self.player_state.max_hp < 500:
            self.player_state.max_hp = 500
        
        self.player_state.hp = self.player_state.max_hp
        
        self.player_state.invincible = False
        self.player_state.berserker_active = False
        self.player_state.voidwalker_timer = 0.0
        self.player_state.reflect_charges = 3 if self.save_data["upgrades"]["reflect"] else 0
        
        # Shields
        self.player_state.shield_active = self.save_data["upgrades"]["shield"]
        self.player_state.mega_shield_active = self.save_data["upgrades"]["megashield"]
        self.player_state.titan_shield_active = self.save_data["upgrades"]["titanshield"]
        
        # Reset time freeze
        self.time_freeze_active = False
        self.time_freeze_end = 0
        
        # Reset boss AI
        self.boss_ai.reset(level)
        
        # Clear projectiles
        self.boss_ai.clear_all_projectiles()
        self.player.clear_projectiles()
        
        # Clear animations
        self.animation_manager.animations.clear()
        self.animation_manager.particles.clear()
        self.animation_manager.trail.clear()
        self.animation_manager.hit_flash.clear()
        self.animation_manager.teleport_flash.clear()
        
        # Track multiplayer session start time
        if self.is_multiplayer_mode:
            self.mp_session_start_time = time.time()
            self.mp_session_damage = 0.0
    
    def update(self, dt):
        """Main update loop"""
        # Process network messages
        if self.network_client:
            self.network_client.process_messages()
            self.other_players = self.network_client.get_other_players()
        
        # Handle frame stepping
        if self.admin_state.frame_step_mode and not self.admin_state.can_step:
            return
        
        if self.admin_state.frame_step_mode:
            self.admin_state.can_step = False
        
        # Calculate time scaling
        scaled_dt = dt * self.game_state.time_scale
        
        # Apply ability time effects
        if self.game_state.screen_state == "GAME" and not self.game_state.paused:
            slow_multiplier = 1.0
            
            # Chronoking passive slow
            if "abilities" in self.save_data and self.save_data["abilities"].get("chronoking", 0) > 0:
                slow_multiplier *= max(0.4, 1 - 0.1 * self.save_data["abilities"].get("chronoking", 0))
            
            # Time slow upgrade
            if self.save_data["upgrades"]["timeslow"]:
                slow_multiplier *= 0.5
            
            # Time freeze ability
            if self.time_freeze_active:
                slow_multiplier *= 0.1
            
            scaled_dt *= slow_multiplier
        
        # Update based on state
        if self.game_state.screen_state == "GAME" and not self.game_state.paused:
            self._update_game(scaled_dt, dt)
        
        # Always update these
        self.game_state.update(scaled_dt)
        self.console.update(scaled_dt)
        self.animation_manager.update(scaled_dt)
    
    def _update_game(self, dt, raw_dt):
        """Update game state"""
        now = time.time()
        
        # Check time freeze expiration
        if self.time_freeze_active and now > self.time_freeze_end:
            self.time_freeze_active = False
        
        # Check for timeshatter ability trigger
        if self.ability_manager.can_use_ability("timeshatter", now):
            keys = pygame.key.get_pressed()
            if keys[pygame.K_r] and "abilities" in self.save_data and self.save_data["abilities"].get("timeshatter", 0) > 0:
                stacks = self.save_data["abilities"].get("timeshatter", 0)
                self.time_freeze_active = True
                self.time_freeze_end = now + 2 + stacks * 0.5
                self.ability_manager.use_ability("timeshatter", now)
        
        # Check for shockwave ability trigger
        if self.ability_manager.can_use_ability("shockwave", now):
            keys = pygame.key.get_pressed()
            if keys[pygame.K_f] and "abilities" in self.save_data and self.save_data["abilities"].get("shockwave", 0) > 0:
                stacks = self.save_data["abilities"].get("shockwave", 0)
                radius = 200 + stacks * 30
                
                # Clear projectiles in radius
                px, py = self.player_state.x, self.player_state.y
                for laser in self.boss_ai.lasers[:]:
                    if math.hypot(laser["x"] - px, laser["y"] - py) < radius:
                        self.animation_manager.spawn("explosion", laser["x"], laser["y"], 
                                                    lifetime=0.3, max_radius=20, color=(255,255,0))
                        self.boss_ai.lasers.remove(laser)
                
                for missile in self.boss_ai.homing_missiles[:]:
                    if math.hypot(missile["x"] - px, missile["y"] - py) < radius:
                        self.animation_manager.spawn("explosion", missile["x"], missile["y"], 
                                                    lifetime=0.3, max_radius=20, color=(255,255,0))
                        self.boss_ai.homing_missiles.remove(missile)
                
                for spiral in self.boss_ai.spiral_lasers[:]:
                    if math.hypot(spiral["x"] - px, spiral["y"] - py) < radius:
                        self.animation_manager.spawn("explosion", spiral["x"], spiral["y"], 
                                                    lifetime=0.3, max_radius=20, color=(255,255,0))
                        self.boss_ai.spiral_lasers.remove(spiral)
                
                self.animation_manager.screen_shake(10, 0.3)
                self.ability_manager.use_ability("shockwave", now)
        
        # Update player
        self.player.update(raw_dt, self.game_state.level, self.boss_state)
        
        # Send player state to server
        if self.is_multiplayer_mode and isinstance(self.network_client, NetworkClient) and self.network_client.connected:
            self.network_client.send_player_state(
                self.player_state.x,
                self.player_state.y,
                self.player_state.hp,
                pygame.mouse.get_pressed()[0]
            )
        
        # Update boss AI
        self.boss_ai.update(dt, self.game_state.level, self.player_state, self.time_freeze_active)
        
        # Apply singularity effect to boss projectiles
        if "abilities" in self.save_data and self.save_data["abilities"].get("singularity", 0) > 0:
            self._apply_singularity_to_boss_projectiles(raw_dt)
        
        # Check player hit by boss projectiles
        self._check_player_hits(dt)
        
        # Check boss hit by player projectiles
        self._check_boss_hits()
        
        # Check boss charge collision
        self._check_boss_charge_collision()
        
        # Check chasing laser collision
        self._check_chasing_laser_collision()
        
        # Update parry duration
        if self.player_state.parry_active:
            self.player_state.parry_duration -= raw_dt
            if self.player_state.parry_duration <= 0:
                self.player_state.parry_active = False
        
        # Check win/lose conditions
        if self.player_state.hp <= 0:
            self._handle_gameover()
        
        if self.boss_state.hp <= 0:
            self._handle_victory()
    
    def _apply_singularity_to_boss_projectiles(self, dt):
        """Apply singularity repulsion to boss projectiles - scales with stacks"""
        px, py = self.player_state.x, self.player_state.y
        stacks = self.save_data["abilities"].get("singularity", 0)
        radius = 120 + stacks * 30  # 150 at 1 stack, 270 at 5 stacks
        strength_mult = 0.7 + stacks * 0.3  # 1.0 at 1 stack, 2.2 at 5 stacks

        # Repel regular lasers
        for laser in self.boss_ai.lasers:
            dx_to_player = px - laser["x"]
            dy_to_player = py - laser["y"]
            dist_to_player = math.hypot(dx_to_player, dy_to_player)
            if 0 < dist_to_player < radius:
                repel_strength = (radius - dist_to_player) / radius * 100 * strength_mult
                laser["vx"] -= (dx_to_player / dist_to_player) * repel_strength * dt
                laser["vy"] -= (dy_to_player / dist_to_player) * repel_strength * dt

        # Repel homing missiles
        for missile in self.boss_ai.homing_missiles:
            dx_to_player = px - missile["x"]
            dy_to_player = py - missile["y"]
            dist_to_player = math.hypot(dx_to_player, dy_to_player)
            if 0 < dist_to_player < radius:
                repel_strength = (radius - dist_to_player) / radius * 100 * strength_mult
                repel_angle = math.atan2(-dy_to_player, -dx_to_player)
                missile["angle"] += (repel_angle - missile["angle"]) * 0.1 * dt

        # Repel spiral lasers
        for spiral in self.boss_ai.spiral_lasers:
            dx_to_player = px - spiral["x"]
            dy_to_player = py - spiral["y"]
            dist_to_player = math.hypot(dx_to_player, dy_to_player)
            if 0 < dist_to_player < radius:
                repel_strength = (radius - dist_to_player) / radius * 50 * strength_mult
                spiral["angle"] += repel_strength * dt * 0.1
    
    def _check_boss_charge_collision(self):
        """Check if boss charge attack hits player"""
        if not self.boss_state.charging:
            return
        
        px, py = self.player_state.x, self.player_state.y
        bx, by = self.boss_state.x, self.boss_state.y
        
        is_invincible = self.player_state.invincible or (
            self.save_data["upgrades"]["voidwalker"] and self.player_state.voidwalker_timer < 5
        )
        
        if is_invincible:
            return
        
        if math.hypot(px - bx, py - by) < 70:
            base_damage = 35
            damage = ScalingFormulas.boss_damage(self.game_state.level, base_damage)
            
            self._apply_damage_to_player(damage)
            self.boss_state.charging = False
            self.boss_state.returning_to_center = True
    
    def _check_chasing_laser_collision(self):
        """Check if chasing laser hits player"""
        if not self.boss_ai.chasing_laser:
            return
        
        is_invincible = self.player_state.invincible or (
            self.save_data["upgrades"]["voidwalker"] and self.player_state.voidwalker_timer < 5
        )
        
        if is_invincible:
            return
        
        px, py = self.player_state.x, self.player_state.y
        bx, by = self.boss_state.x, self.boss_state.y
        
        laser = self.boss_ai.chasing_laser
        dx_laser = math.cos(laser["angle"])
        dy_laser = math.sin(laser["angle"])
        end_x = bx + dx_laser * 2000
        end_y = by + dy_laser * 2000
        
        # Calculate distance from point to line
        line_len = math.hypot(end_x - bx, end_y - by)
        if line_len > 0:
            distance = abs((end_y - by) * px - (end_x - bx) * py + end_x * by - end_y * bx) / line_len
            dot_product = (px - bx) * dx_laser + (py - by) * dy_laser
            
            if distance < laser["width"] and dot_product > 0:
                base_damage = 30
                damage = ScalingFormulas.boss_damage(self.game_state.level, base_damage)
                
                # Check laser null
                if self.save_data["upgrades"]["lasernull"] and time.time() % 0.1 < 0.05:
                    return
                
                self._apply_damage_to_player(damage)
                laser["angle"] += 0.1
    
    def _check_player_hits(self, dt):
        """Check if player is hit by boss projectiles"""
        px, py = self.player_state.x, self.player_state.y
        is_invincible = self.player_state.invincible or (
            self.save_data["upgrades"]["voidwalker"] and self.player_state.voidwalker_timer < 5
        )
        
        if is_invincible:
            return
        
        hit = False
        damage = 0
        
        # Check lasers
        for laser in self.boss_ai.lasers[:]:
            if abs(laser["x"] - px) < 25 and abs(laser["y"] - py) < 25:
                if self.save_data["upgrades"]["lasernull"] and time.time() % 0.1 < 0.05:
                    self.boss_ai.lasers.remove(laser)
                    continue
                base_damage = 12
                damage = ScalingFormulas.boss_damage(self.game_state.level, base_damage)
                hit = True
                self.boss_ai.lasers.remove(laser)
                break
        
        # Check homing missiles
        if not hit:
            for missile in self.boss_ai.homing_missiles[:]:
                if abs(missile["x"] - px) < 25 and abs(missile["y"] - py) < 25:
                    base_damage = 20
                    damage = ScalingFormulas.boss_damage(self.game_state.level, base_damage)
                    hit = True
                    self.boss_ai.homing_missiles.remove(missile)
                    break
        
        # Check spiral lasers
        if not hit:
            for spiral in self.boss_ai.spiral_lasers[:]:
                if abs(spiral["x"] - px) < 25 and abs(spiral["y"] - py) < 25:
                    if self.save_data["upgrades"]["lasernull"] and time.time() % 0.1 < 0.05:
                        self.boss_ai.spiral_lasers.remove(spiral)
                        continue
                    base_damage = 15
                    damage = ScalingFormulas.boss_damage(self.game_state.level, base_damage)
                    hit = True
                    self.boss_ai.spiral_lasers.remove(spiral)
                    break
        
        if hit:
            self._apply_damage_to_player(damage)
            self.animation_manager.screen_shake(4, 0.1)
    
    def _apply_damage_to_player(self, damage):
        """Apply damage to player with shields/parry"""
        if self.player_state.parry_active and self.save_data["upgrades"]["parry"]:
            self.boss_state.hp -= 25
            self.player_state.parry_active = False
            self.animation_manager.spawn("explosion", self.player_state.x, self.player_state.y,
                                        lifetime=0.3, max_radius=40, color=(0,255,255))
            self.animation_manager.screen_shake(6, 0.2)
        elif self.player_state.reflect_charges > 0:
            self.player_state.reflect_charges -= 1
            self.boss_state.hp -= 20
            self.animation_manager.spawn("explosion", self.player_state.x, self.player_state.y,
                                        lifetime=0.3, max_radius=30, color=(255,215,0))
        elif self.player_state.titan_shield_active:
            self.player_state.titan_shield_active = False
        elif self.player_state.mega_shield_active:
            self.player_state.mega_shield_active = False
        elif self.player_state.shield_active:
            self.player_state.shield_active = False
            self.save_data["upgrades"]["shield"] = False
            save_progress(self.save_data)
        else:
            self.player_state.hp -= damage
            if self.player_state.hp <= 0 and self.save_data["upgrades"]["immortal"]:
                self.player_state.hp = self.player_state.max_hp * 0.5
                self.save_data["upgrades"]["immortal"] = False
                save_progress(self.save_data)
    
    def _check_boss_hits(self):
        """Check if boss is hit by player projectiles - FIXED VERSION"""
        for projectile in self.player.projectiles[:]:
            px, py = projectile["x"], projectile["y"]
            if abs(px - self.boss_state.x) < 60 and abs(py - self.boss_state.y) < 60:
                # FIX: Skip if this piercing bullet already hit boss (prevent orbit/double damage)
                if projectile.get("piercing") and projectile.get("has_hit_boss"):
                    continue
                
                self.boss_state.hp -= projectile["dmg"]
                
                # Track damage for multiplayer stats
                if self.is_multiplayer_mode:
                    self.mp_session_damage += projectile["dmg"]
                
                # Send to server in multiplayer
                if self.is_multiplayer_mode and isinstance(self.network_client, NetworkClient) and self.network_client.connected:
                    self.network_client.send_boss_hit(projectile["dmg"])
                
                # Lifesteal
                if self.save_data["upgrades"]["lifesteal"]:
                    self.player_state.hp = min(self.player_state.hp + 0.5, self.player_state.max_hp)
                if self.save_data["upgrades"]["vampire"]:
                    self.player_state.hp = min(self.player_state.hp + 1, self.player_state.max_hp)
                
                # Explosions
                if projectile.get("nuclear"):
                    for i in range(16):
                        angle = i * 22.5
                        offset_x = math.cos(math.radians(angle)) * 30
                        offset_y = math.sin(math.radians(angle)) * 30
                        self.animation_manager.spawn("explosion", px + offset_x, py + offset_y, 
                                                    lifetime=0.5, max_radius=40, color=(0,255,0))
                    self.boss_state.hp -= projectile["dmg"] * 2
                    self.animation_manager.screen_shake(12, 0.3)
                elif projectile.get("explosive"):
                    for i in range(8):
                        angle = i * 45
                        offset_x = math.cos(math.radians(angle)) * 15
                        offset_y = math.sin(math.radians(angle)) * 15
                        self.animation_manager.spawn("explosion", px + offset_x, py + offset_y, 
                                                    lifetime=0.3, max_radius=30, color=(255,150,0))
                    self.animation_manager.screen_shake(6, 0.2)
                
                self.animation_manager.enemy_hit_effect(px, py)
                self.boss_state.emotion = "hurt"
                
                # FIX: Mark piercing bullets as having hit boss to prevent re-homing
                if projectile.get("piercing"):
                    projectile["has_hit_boss"] = True
                else:
                    self.player.projectiles.remove(projectile)
    
    def _handle_victory(self):
        """Handle level completion"""
        level = self.game_state.level
        
        coin_reward = ScalingFormulas.coin_reward(level)
        
        self.game_state.coins += coin_reward
        self.save_data["coins"] = self.game_state.coins
        
        if level + 1 > self.game_state.max_level:
            self.game_state.max_level = level + 1
            self.save_data["max_level"] = self.game_state.max_level
        
        # Save to appropriate file based on mode
        if self.is_multiplayer_mode:
            # Update multiplayer stats
            time_played = time.time() - self.mp_session_start_time if self.mp_session_start_time > 0 else 0
            update_multiplayer_stats(
                self.save_data, 
                games_won=1, 
                damage_dealt=self.mp_session_damage,
                bosses_killed=1,
                time_played=time_played
            )
            save_multiplayer_progress(self.save_data)
            self.mp_session_damage = 0.0  # Reset for next round
        else:
            save_progress(self.save_data)
        
        self.game_state.screen_state = "VICTORY"
    
    def _handle_gameover(self):
        """Handle player death"""
        # Save multiplayer stats on death
        if self.is_multiplayer_mode:
            time_played = time.time() - self.mp_session_start_time if self.mp_session_start_time > 0 else 0
            update_multiplayer_stats(
                self.save_data, 
                games_won=0, 
                damage_dealt=self.mp_session_damage,
                bosses_killed=0,
                deaths=1,
                time_played=time_played
            )
            save_multiplayer_progress(self.save_data)
            self.mp_session_damage = 0.0
        
        self.game_state.screen_state = "GAMEOVER"
    
    def render(self):
        """Main render loop"""
        # Apply screen shake offset during game
        shake_x, shake_y = self.animation_manager.get_shake_offset()
        if self.game_state.screen_state == "GAME" and (shake_x or shake_y):
            self.screen.fill((0, 0, 0))
            game_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            game_surface.fill((8, 8, 35))
            # Temporarily redirect rendering to game_surface
            original_screen = self.screen
            self.screen = game_surface
            self.renderer.screen = game_surface
        else:
            self.screen.fill((8, 8, 35))
            original_screen = None

        # Render based on state
        action = None

        if self.game_state.screen_state == "MENU":
            action = self.ui_manager.render_menu(self.game_state)
        
        elif self.game_state.screen_state == "LEVELSELECT":
            action = self.ui_manager.render_level_select(self.game_state)
        
        elif self.game_state.screen_state == "SHOP_MENU":
            action = self.ui_manager.render_shop_menu()
        
        elif self.game_state.screen_state == "SHOP":
            action = self.ui_manager.render_shop(self.game_state)
        
        elif self.game_state.screen_state == "ABILITY_TEMPLE":
            action = self.ui_manager.render_ability_temple(self.game_state, self.ability_manager)
        
        elif self.game_state.screen_state == "SETTINGS":
            action = self.ui_manager.render_settings()
        
        elif self.game_state.screen_state == "ADMIN_MENU":
            action = self.ui_manager.render_admin_menu(self.admin_state)
        
        elif self.game_state.screen_state == "MULTIPLAYER_MENU":
            action = self.ui_manager.render_multiplayer_menu(self.game_state)
        
        elif self.game_state.screen_state == "MULTIPLAYER_LOBBY":
            action = self.ui_manager.render_multiplayer_lobby(self.game_state)
        
        elif self.game_state.screen_state == "PVP_LOBBY":
            action = self.ui_manager.render_pvp_lobby(self.game_state)
        
        elif self.game_state.screen_state == "GAME":
            if self.game_state.paused:
                self.renderer.render_game(self.game_state, self.player_state, self.boss_state,
                                        self.boss_ai, self.player, self.animation_manager,
                                        self.ability_manager, self.save_data)
                # Render other players in multiplayer
                if self.is_multiplayer_mode:
                    self._render_other_players()
                action = self.ui_manager.render_pause_menu()
            else:
                self.renderer.render_game(self.game_state, self.player_state, self.boss_state,
                                        self.boss_ai, self.player, self.animation_manager,
                                        self.ability_manager, self.save_data)
                # Render other players in multiplayer
                if self.is_multiplayer_mode:
                    self._render_other_players()
        
        elif self.game_state.screen_state == "VICTORY":
            action = self.ui_manager.render_victory(self.game_state)
        
        elif self.game_state.screen_state == "GAMEOVER":
            action = self.ui_manager.render_gameover(self.game_state)
        
        # Handle action from rendering
        if action:
            self._handle_ui_action(action)
        
        # If we used a game surface for screen shake, blit it with offset
        if original_screen is not None:
            self.screen = original_screen
            self.renderer.screen = original_screen
            original_screen.blit(game_surface, (shake_x, shake_y))

        # Always render console on top
        self.console.render(self.screen)

        # Debug stats
        if self.admin_state.show_stats:
            self._render_debug_stats()

        pygame.display.flip()
    
    def _render_other_players(self):
        """Render other players in multiplayer"""
        for player_id, data in self.other_players.items():
            x = data.get("x", 0)
            y = data.get("y", 0)
            name = data.get("name", "Player")
            is_bot = data.get("is_bot", False)
            
            # Draw player indicator
            color = (100, 200, 255) if not is_bot else (255, 200, 100)
            pygame.draw.circle(self.screen, color, (int(x), int(y)), 12, 3)
            
            # Draw name
            font = pygame.font.Font(None, 20)
            name_text = font.render(name, True, color)
            self.screen.blit(name_text, (int(x) - name_text.get_width()//2, int(y) - 25))
    
    def _render_debug_stats(self):
        """Render debug overlay"""
        font = pygame.font.Font(None, 24)
        y = 10
        stats = [
            f"Level: {self.game_state.level}",
            f"FPS: {int(self.clock.get_fps())}",
            f"Player HP: {int(self.player_state.hp)}/{int(self.player_state.max_hp)}",
            f"Boss HP: {int(self.boss_state.hp)}/{int(self.boss_state.max_hp)}",
            f"Time Scale: {self.game_state.time_scale:.2f}",
            f"Projectiles: P:{len(self.player.projectiles)} B:{len(self.boss_ai.lasers)}",
            f"Time Freeze: {self.time_freeze_active}",
            f"Mode: {self.mode.value}",
        ]
        
        if self.is_multiplayer_mode:
            stats.append(f"Players: {len(self.other_players) + 1}")
            stats.append(f"Bots: {self.get_bot_count()}")
            if self.network_client:
                stats.append(f"Latency: {self.network_client.latency:.1f}ms")
        
        for stat in stats:
            text = font.render(stat, True, (255, 255, 0))
            self.screen.blit(text, (10, y))
            y += 25
    
    def run(self):
        """Main game loop"""
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            
            self.handle_events()
            self.update(dt)
            self.render()
        
        self._cleanup_network()
        pygame.quit()
        sys.exit()


def main():
    """Main entry point with command line arguments"""
    parser = argparse.ArgumentParser(description="Cube Boss Fight - Ultimate Edition")
    parser.add_argument("--multiplayer", "-m", action="store_true", help="Start in multiplayer mode")
    parser.add_argument("--host", "-H", action="store_true", help="Host a game server")
    parser.add_argument("--server", "-s", default="127.0.0.1", help="Server address to connect to")
    parser.add_argument("--port", "-p", type=int, default=5555, help="Server port")
    parser.add_argument("--bots", "-b", type=int, default=0, help="Number of bots to add (host only)")
    
    args = parser.parse_args()
    
    mode = GameMode.MULTIPLAYER if args.multiplayer or args.host else GameMode.SINGLEPLAYER
    
    game = Game(
        mode=mode,
        host_server=args.host,
        server_address=args.server,
        server_port=args.port
    )
    
    # Add bots if hosting
    if args.host and args.bots > 0:
        for i in range(args.bots):
            game.add_bot(f"Bot_{i+1}")
    
    game.run()


if __name__ == "__main__":
    main()

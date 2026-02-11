"""
FILE: game/ui.py
Complete UI rendering with all visual polish and multiplayer support
"""

import pygame
import math
import time
import random
from typing import Optional, Dict, Any, List

class UIManager:
    """Manages all UI rendering and interactions"""
    
    def __init__(self, screen, save_data):
        self.screen = screen
        self.save_data = save_data
        
        self.font_big = pygame.font.Font(None, 60)
        self.font_med = pygame.font.Font(None, 40)
        self.font_small = pygame.font.Font(None, 30)
        self.font_tiny = pygame.font.Font(None, 24)
        
        self.level_scroll = 0
        self.shop_scroll = 0
        self.admin_input = ""
        
        # Ability temple rolling
        self.rolling = False
        self.roll_start = 0
        self.roll_duration = 0.6
        
        # Multiplayer UI state
        self.server_ip_input = "127.0.0.1"
        self.server_port_input = "5555"
        self.player_name_input = "Player"
        self.lobby_scroll = 0
        self.chat_input = ""
        self.chat_messages: List[tuple] = []  # (sender, message, timestamp)
        self.active_input_field = None  # "ip", "port", "name", "chat"
        
        # Connection status
        self.connection_status = "disconnected"
        self.connection_error = ""
        self.players_in_lobby: List[Dict] = []
        
        # Button click tracking (to prevent multiple triggers per frame)
        self.mouse_was_pressed = False
        self.frame_click_processed = False  # Track if we've processed a click this frame
    
    def set_connection_status(self, status: str, error: str = ""):
        """Update connection status display"""
        self.connection_status = status
        self.connection_error = error
    
    def set_lobby_players(self, players: List[Dict]):
        """Update player list in lobby"""
        self.players_in_lobby = players
    
    def add_chat_message(self, sender: str, message: str):
        """Add chat message to display"""
        self.chat_messages.append((sender, message, time.time()))
        # Keep last 50 messages
        if len(self.chat_messages) > 50:
            self.chat_messages.pop(0)
    
    def handle_event(self, event, game_state, player_state, boss_state, ability_manager, save_data):
        """Handle UI events, return action dict if any"""
        # Reset button state tracking on mouse button up
        if event.type == pygame.MOUSEBUTTONUP:
            self.mouse_was_pressed = False
            self.frame_click_processed = False
        
        # Scroll handling
        if event.type == pygame.MOUSEWHEEL:
            if game_state.screen_state == "LEVELSELECT":
                self.level_scroll -= event.y * 30
                max_scroll = max(0, ((game_state.max_level - 1) // 5) * 100 - 300)
                self.level_scroll = max(0, min(self.level_scroll, max_scroll))
            
            elif game_state.screen_state == "SHOP":
                self.shop_scroll -= event.y * 30
                self.shop_scroll = max(0, min(self.shop_scroll, 1900))
            
            elif game_state.screen_state == "MULTIPLAYER_LOBBY":
                self.lobby_scroll -= event.y * 20
                self.lobby_scroll = max(0, self.lobby_scroll)
        
        # Admin password input
        if game_state.screen_state == "ADMIN_MENU" and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                self.admin_input = self.admin_input[:-1]
            elif event.key == pygame.K_RETURN:
                if self.admin_input == "ilovenoodledoo":
                    save_data["settings"]["admin"] = True
                    from core.config import save_progress
                    save_progress(save_data)
                    self.admin_input = ""
                    return {"type": "change_state", "state": "MENU"}
                else:
                    self.admin_input = ""
            elif len(self.admin_input) < 20 and event.unicode.isprintable():
                self.admin_input += event.unicode
        
        # Multiplayer lobby input
        if game_state.screen_state in ["MULTIPLAYER_LOBBY", "PVP_LOBBY"] and event.type == pygame.KEYDOWN:
            return self._handle_lobby_input(event)
        
        return None
    
    def _handle_lobby_input(self, event) -> Optional[Dict]:
        """Handle keyboard input in multiplayer lobby"""
        if self.active_input_field == "ip":
            if event.key == pygame.K_BACKSPACE:
                self.server_ip_input = self.server_ip_input[:-1]
            elif event.key == pygame.K_TAB:
                self.active_input_field = "port"
            elif event.key == pygame.K_RETURN:
                return {"type": "connect_to_server", "ip": self.server_ip_input, "port": int(self.server_port_input)}
            elif event.unicode.isprintable() and len(self.server_ip_input) < 45:
                self.server_ip_input += event.unicode
        
        elif self.active_input_field == "port":
            if event.key == pygame.K_BACKSPACE:
                self.server_port_input = self.server_port_input[:-1]
            elif event.key == pygame.K_TAB:
                self.active_input_field = "name"
            elif event.key == pygame.K_RETURN:
                return {"type": "connect_to_server", "ip": self.server_ip_input, "port": int(self.server_port_input)}
            elif event.unicode.isdigit() and len(self.server_port_input) < 5:
                self.server_port_input += event.unicode
        
        elif self.active_input_field == "name":
            if event.key == pygame.K_BACKSPACE:
                self.player_name_input = self.player_name_input[:-1]
            elif event.key == pygame.K_TAB:
                self.active_input_field = "chat"
            elif event.unicode.isprintable() and len(self.player_name_input) < 16:
                self.player_name_input += event.unicode
        
        elif self.active_input_field == "chat":
            if event.key == pygame.K_BACKSPACE:
                self.chat_input = self.chat_input[:-1]
            elif event.key == pygame.K_RETURN and self.chat_input.strip():
                msg = self.chat_input.strip()
                self.chat_input = ""
                return {"type": "send_chat", "message": msg}
            elif event.key == pygame.K_TAB:
                self.active_input_field = "ip"
            elif event.unicode.isprintable() and len(self.chat_input) < 100:
                self.chat_input += event.unicode
        
        return None
    
    def render_menu(self, game_state):
        """Render main menu"""
        # Reset frame click tracking and update mouse state at start of render
        self.frame_click_processed = False
        current_mouse_pressed = pygame.mouse.get_pressed()[0]
        if not current_mouse_pressed:
            self.mouse_was_pressed = False
        
        title_y = 100 + math.sin(time.time() * 2) * 5
        title = self.font_big.render("CUBE BOSS FIGHT", True, (255, 215, 0))
        self.screen.blit(title, (200, int(title_y)))
        
        coins = self.font_med.render(f"Coins: {game_state.coins}", True, (255, 215, 0))
        self.screen.blit(coins, (308, 180))
        
        max_lv = self.font_small.render(f"Max Level: {game_state.max_level}", True, (150, 255, 150))
        self.screen.blit(max_lv, (310, 220))
        
        # Check all buttons (using elif prevents multiple triggers)
        if self._button("LEVEL SELECT", 300, 280, 200, 60, (0, 100, 200), (0, 150, 255)):
            self.mouse_was_pressed = current_mouse_pressed
            return {"type": "change_state", "state": "LEVELSELECT"}
        if self._button("SHOP", 300, 360, 200, 60, (0, 100, 200), (0, 150, 255)):
            self.mouse_was_pressed = current_mouse_pressed
            return {"type": "change_state", "state": "SHOP_MENU"}
        if self._button("MULTIPLAYER", 300, 440, 200, 60, (100, 50, 150), (150, 80, 200)):
            self.mouse_was_pressed = current_mouse_pressed
            return {"type": "change_state", "state": "MULTIPLAYER_MENU"}
        if self._button("SETTINGS", 50, 500, 150, 60, (0, 100, 200), (0, 150, 255)):
            self.mouse_was_pressed = current_mouse_pressed
            return {"type": "change_state", "state": "SETTINGS"}
        if self._button("RESET GAME", 600, 500, 150, 60, (150, 0, 0), (255, 0, 0)):
            self.mouse_was_pressed = current_mouse_pressed
            return {"type": "reset_save"}
        
        # Update mouse state at end of frame for next frame
        self.mouse_was_pressed = current_mouse_pressed
        return None
    
    def render_multiplayer_menu(self, game_state):
        """Render multiplayer menu screen"""
        # Reset frame click tracking and update mouse state at start of render
        self.frame_click_processed = False
        current_mouse_pressed = pygame.mouse.get_pressed()[0]
        if not current_mouse_pressed:
            self.mouse_was_pressed = False
        
        title = self.font_big.render("MULTIPLAYER", True, (200, 150, 255))
        self.screen.blit(title, (250, 30))
        
        subtitle = self.font_small.render("Choose a mode:", True, (200, 200, 200))
        self.screen.blit(subtitle, (300, 100))
        
        # Co-op mode (boss fight together)
        if self._button("CO-OP MODE", 300, 180, 200, 60, (100, 50, 150), (150, 80, 200)):
            self.mouse_was_pressed = current_mouse_pressed
            return {"type": "change_state", "state": "MULTIPLAYER_LOBBY", "mode": "coop"}
        
        # PvP mode (players fight each other)
        if self._button("PvP MODE", 300, 260, 200, 60, (150, 50, 50), (200, 80, 80)):
            self.mouse_was_pressed = current_mouse_pressed
            return {"type": "change_state", "state": "PVP_LOBBY", "mode": "pvp"}
        
        # Back button
        if self._button("BACK", 300, 400, 200, 60, (150, 0, 0), (200, 0, 0)):
            self.mouse_was_pressed = current_mouse_pressed
            return {"type": "change_state", "state": "MENU"}
        
        # Update mouse state at end of frame
        self.mouse_was_pressed = current_mouse_pressed
        return None
    
    def render_multiplayer_lobby(self, game_state):
        """Render multiplayer lobby screen"""
        # Reset frame click tracking and update mouse state at start of render
        self.frame_click_processed = False
        current_mouse_pressed = pygame.mouse.get_pressed()[0]
        if not current_mouse_pressed:
            self.mouse_was_pressed = False
        
        title = self.font_big.render("MULTIPLAYER", True, (200, 150, 255))
        self.screen.blit(title, (250, 30))
        
        # Connection status
        status_color = {
            "disconnected": (150, 150, 150),
            "connecting": (255, 200, 0),
            "connected": (0, 255, 0),
            "error": (255, 0, 0)
        }.get(self.connection_status, (150, 150, 150))
        
        status_text = self.font_small.render(f"Status: {self.connection_status.upper()}", True, status_color)
        self.screen.blit(status_text, (50, 90))
        
        if self.connection_error:
            error_text = self.font_tiny.render(self.connection_error, True, (255, 100, 100))
            self.screen.blit(error_text, (50, 115))
        
        # Server input fields
        self._render_input_field("Server IP:", self.server_ip_input, 50, 150, 300, "ip")
        self._render_input_field("Port:", self.server_port_input, 370, 150, 80, "port")
        self._render_input_field("Name:", self.player_name_input, 470, 150, 150, "name")
        
        # Connect/Host buttons
        if self._button("HOST", 50, 210, 120, 50, (0, 120, 0), (0, 180, 0)):
            self.mouse_was_pressed = current_mouse_pressed
            return {"type": "host_game", "port": int(self.server_port_input) if self.server_port_input else 5555, "name": self.player_name_input}
        
        if self._button("JOIN", 190, 210, 120, 50, (0, 100, 200), (0, 150, 255)):
            self.mouse_was_pressed = current_mouse_pressed
            return {"type": "connect_to_server", "ip": self.server_ip_input or "127.0.0.1", "port": int(self.server_port_input) if self.server_port_input else 5555, "name": self.player_name_input}
        
        if self._button("DISCONNECT", 330, 210, 150, 50, (150, 0, 0), (200, 0, 0)):
            self.mouse_was_pressed = current_mouse_pressed
            return {"type": "disconnect"}
        
        # Player list
        pygame.draw.rect(self.screen, (30, 30, 50), (50, 280, 300, 200))
        pygame.draw.rect(self.screen, (100, 100, 150), (50, 280, 300, 200), 2)
        
        players_title = self.font_small.render("Players in Lobby:", True, (255, 255, 255))
        self.screen.blit(players_title, (60, 285))
        
        y = 315
        for player in self.players_in_lobby[:6]:
            name = player.get("name", "Unknown")
            ready = player.get("ready", False)
            is_host = player.get("is_host", False)
            
            color = (0, 255, 0) if ready else (200, 200, 200)
            prefix = "[HOST] " if is_host else ""
            suffix = " (Ready)" if ready else ""
            
            player_text = self.font_tiny.render(f"{prefix}{name}{suffix}", True, color)
            self.screen.blit(player_text, (60, y))
            y += 25
        
        # Chat area
        pygame.draw.rect(self.screen, (30, 30, 50), (370, 280, 380, 200))
        pygame.draw.rect(self.screen, (100, 100, 150), (370, 280, 380, 200), 2)
        
        chat_title = self.font_small.render("Chat:", True, (255, 255, 255))
        self.screen.blit(chat_title, (380, 285))
        
        # Chat messages
        y = 310
        for sender, msg, timestamp in self.chat_messages[-6:]:
            chat_text = self.font_tiny.render(f"{sender}: {msg}", True, (200, 200, 255))
            self.screen.blit(chat_text, (380, y))
            y += 22
        
        # Chat input
        self._render_input_field("", self.chat_input, 370, 450, 380, "chat")
        
        # Ready/Start buttons
        if self._button("READY", 50, 500, 120, 50, (0, 100, 0), (0, 150, 0)):
            self.mouse_was_pressed = current_mouse_pressed
            return {"type": "ready"}
        
        if self._button("START GAME", 190, 500, 160, 50, (150, 100, 0), (200, 150, 0)):
            self.mouse_was_pressed = current_mouse_pressed
            return {"type": "start_multiplayer_game"}
        
        if self._button("BACK", 600, 500, 150, 50, (150, 0, 0), (200, 0, 0)):
            self.mouse_was_pressed = current_mouse_pressed
            return {"type": "change_state", "state": "MENU"}
        
        # Update mouse state at end of frame
        self.mouse_was_pressed = current_mouse_pressed
        return None
    
    def render_pvp_lobby(self, game_state):
        """Render PvP lobby screen (similar to multiplayer lobby but for PvP)"""
        # Reset frame click tracking and update mouse state at start of render
        self.frame_click_processed = False
        current_mouse_pressed = pygame.mouse.get_pressed()[0]
        if not current_mouse_pressed:
            self.mouse_was_pressed = False
        
        title = self.font_big.render("PvP MODE", True, (255, 100, 100))
        self.screen.blit(title, (280, 30))
        
        subtitle = self.font_small.render("Player vs Player - Fight other players!", True, (200, 200, 200))
        self.screen.blit(subtitle, (200, 90))
        
        # Connection status
        status_color = {
            "disconnected": (150, 150, 150),
            "connecting": (255, 200, 0),
            "connected": (0, 255, 0),
            "error": (255, 0, 0)
        }.get(self.connection_status, (150, 150, 150))
        
        status_text = self.font_small.render(f"Status: {self.connection_status.upper()}", True, status_color)
        self.screen.blit(status_text, (50, 130))
        
        if self.connection_error:
            error_text = self.font_tiny.render(self.connection_error, True, (255, 100, 100))
            self.screen.blit(error_text, (50, 155))
        
        # Server input fields
        self._render_input_field("Server IP:", self.server_ip_input, 50, 190, 300, "ip")
        self._render_input_field("Port:", self.server_port_input, 370, 190, 80, "port")
        self._render_input_field("Name:", self.player_name_input, 470, 190, 150, "name")
        
        # Connect/Host buttons
        if self._button("HOST PvP", 50, 250, 120, 50, (150, 0, 0), (200, 0, 0)):
            self.mouse_was_pressed = current_mouse_pressed
            return {"type": "host_game", "port": int(self.server_port_input) if self.server_port_input else 5555, "name": self.player_name_input, "mode": "pvp"}
        
        if self._button("JOIN PvP", 190, 250, 120, 50, (200, 0, 0), (255, 50, 50)):
            self.mouse_was_pressed = current_mouse_pressed
            return {"type": "connect_to_server", "ip": self.server_ip_input or "127.0.0.1", "port": int(self.server_port_input) if self.server_port_input else 5555, "name": self.player_name_input, "mode": "pvp"}
        
        if self._button("DISCONNECT", 330, 250, 150, 50, (150, 0, 0), (200, 0, 0)):
            self.mouse_was_pressed = current_mouse_pressed
            return {"type": "disconnect"}
        
        # Player list
        pygame.draw.rect(self.screen, (30, 30, 50), (50, 320, 300, 200))
        pygame.draw.rect(self.screen, (150, 100, 100), (50, 320, 300, 200), 2)
        
        players_title = self.font_small.render("Players in Lobby:", True, (255, 255, 255))
        self.screen.blit(players_title, (60, 325))
        
        y = 355
        for player in self.players_in_lobby[:6]:
            name = player.get("name", "Unknown")
            ready = player.get("ready", False)
            is_host = player.get("is_host", False)
            
            color = (0, 255, 0) if ready else (200, 200, 200)
            prefix = "[HOST] " if is_host else ""
            suffix = " (Ready)" if ready else ""
            
            player_text = self.font_tiny.render(f"{prefix}{name}{suffix}", True, color)
            self.screen.blit(player_text, (60, y))
            y += 25
        
        # Chat area
        pygame.draw.rect(self.screen, (30, 30, 50), (370, 320, 380, 200))
        pygame.draw.rect(self.screen, (150, 100, 100), (370, 320, 380, 200), 2)
        
        chat_title = self.font_small.render("Chat:", True, (255, 255, 255))
        self.screen.blit(chat_title, (380, 325))
        
        # Chat messages
        y = 350
        for sender, msg, timestamp in self.chat_messages[-6:]:
            chat_text = self.font_tiny.render(f"{sender}: {msg}", True, (255, 200, 200))
            self.screen.blit(chat_text, (380, y))
            y += 22
        
        # Chat input
        self._render_input_field("", self.chat_input, 370, 490, 380, "chat")
        
        # Ready/Start buttons
        if self._button("READY", 50, 540, 120, 50, (0, 100, 0), (0, 150, 0)):
            self.mouse_was_pressed = current_mouse_pressed
            return {"type": "ready"}
        
        if self._button("START PvP", 190, 540, 160, 50, (200, 0, 0), (255, 50, 50)):
            self.mouse_was_pressed = current_mouse_pressed
            return {"type": "start_multiplayer_game"}
        
        if self._button("BACK", 600, 540, 150, 50, (150, 0, 0), (200, 0, 0)):
            self.mouse_was_pressed = current_mouse_pressed
            return {"type": "change_state", "state": "MULTIPLAYER_MENU"}
        
        # Update mouse state at end of frame
        self.mouse_was_pressed = current_mouse_pressed
        return None
    
    def _render_input_field(self, label: str, text: str, x: int, y: int, width: int, field_id: str):
        """Render a text input field"""
        if label:
            label_surf = self.font_tiny.render(label, True, (200, 200, 200))
            self.screen.blit(label_surf, (x, y))
            y += 20
        
        # Background
        is_active = self.active_input_field == field_id
        bg_color = (50, 50, 70) if is_active else (30, 30, 40)
        border_color = (100, 150, 255) if is_active else (80, 80, 100)
        
        rect = pygame.Rect(x, y, width, 30)
        pygame.draw.rect(self.screen, bg_color, rect)
        pygame.draw.rect(self.screen, border_color, rect, 2)
        
        # Text
        text_surf = self.font_tiny.render(text, True, (255, 255, 255))
        self.screen.blit(text_surf, (x + 5, y + 5))
        
        # Cursor
        if is_active and int(time.time() * 2) % 2 == 0:
            cursor_x = x + 5 + self.font_tiny.size(text)[0]
            pygame.draw.line(self.screen, (255, 255, 255), (cursor_x, y + 5), (cursor_x, y + 25), 2)
        
        # Click detection
        mouse = pygame.mouse.get_pos()
        click = pygame.mouse.get_pressed()[0]
        if rect.collidepoint(mouse) and click:
            self.active_input_field = field_id
    
    def render_level_select(self, game_state):
        """Render level selection screen"""
        # Reset frame click tracking and update mouse state at start of render
        self.frame_click_processed = False
        current_mouse_pressed = pygame.mouse.get_pressed()[0]
        if not current_mouse_pressed:
            self.mouse_was_pressed = False
        
        title = self.font_big.render("SELECT LEVEL", True, (255, 215, 0))
        self.screen.blit(title, (200, 40))
        
        # Scroll hints
        if self.level_scroll > 0:
            scroll_hint = self.font_small.render("^ Scroll Up", True, (150, 150, 150))
            self.screen.blit(scroll_hint, (320, 90))
        
        max_scroll = max(0, ((game_state.max_level - 1) // 5) * 100 - 300)
        if self.level_scroll < max_scroll:
            scroll_hint = self.font_small.render("v Scroll Down", True, (150, 150, 150))
            self.screen.blit(scroll_hint, (310, 500))
        
        for i in range(game_state.max_level):
            r, c = divmod(i, 5)
            lvl = i + 1
            y_pos = 140 + r * 100 - self.level_scroll
            
            if -80 <= y_pos <= 600:
                btn_color = (200, 0, 200) if lvl % 10 == 0 else (0, 100, 200)
                btn_hover = (255, 0, 255) if lvl % 10 == 0 else (0, 150, 255)
                
                if self._button(str(lvl), 120 + c*120, y_pos, 100, 80, btn_color, btn_hover):
                    self.mouse_was_pressed = current_mouse_pressed
                    return {"type": "start_level", "level": lvl}
        
        # Scroll buttons
        max_scroll = max(0, ((game_state.max_level - 1) // 5) * 100 - 300)
        
        if max_scroll > 0:
            if self._button("â–² TOP", 50, 100, 60, 40, (60, 60, 80), (100, 100, 120)):
                self.level_scroll = 0
                self.mouse_was_pressed = current_mouse_pressed
            
            if self._button("â–¼ END", 50, 490, 60, 40, (60, 60, 80), (100, 100, 120)):
                self.level_scroll = max_scroll
                self.mouse_was_pressed = current_mouse_pressed
        
        if self._button("BACK", 300, 540, 200, 60, (150, 0, 0), (200, 0, 0)):
            self.mouse_was_pressed = current_mouse_pressed
            return {"type": "change_state", "state": "MENU"}
        
        # Update mouse state at end of frame
        self.mouse_was_pressed = current_mouse_pressed
        return None
    
    def render_shop_menu(self):
        """Render shop selection menu"""
        title = self.font_big.render("SHOP", True, (255, 215, 0))
        self.screen.blit(title, (330, 100))
        
        if self._button("Normal Shop", 250, 240, 300, 70, (0, 120, 200), (0, 170, 255)):
            return {"type": "change_state", "state": "SHOP"}
        
        if self._button("Ability Temple", 250, 340, 300, 70, (160, 80, 200), (220, 120, 255)):
            return {"type": "enter_temple"}
        
        if self._button("BACK", 300, 450, 200, 60, (150, 0, 0), (200, 0, 0)):
            return {"type": "change_state", "state": "MENU"}
        
        return None
    
    def render_shop(self, game_state):
        """Render upgrade shop"""
        title = self.font_big.render("SHOP", True, (255, 215, 0))
        self.screen.blit(title, (330, 30))
        
        coins = self.font_med.render(f"Coins: {game_state.coins}", True, (255, 215, 0))
        self.screen.blit(coins, (300, 90))
        
        max_lv = self.font_tiny.render(f"Max Level: {game_state.max_level}", True, (150, 200, 150))
        self.screen.blit(max_lv, (340, 125))
        
        items = [
            ("Damage+", "damage", 50, 30, "Increase bullet damage", 1),
            ("Fire Rate+", "firerate", 80, 30, "Shoot faster", 1),
            ("Max HP+", "health", 100, 20, "Increase max health", 1),
            ("Speed+", "speed", 60, 15, "Bullets move faster", 1),
            ("Triple Shot", "triple", 250, 1, "Fire 3 bullets at once", 1),
            ("Rapid Fire", "rapid", 350, 1, "Halve fire rate cooldown", 3),
            ("Shield", "shield", 300, 1, "Block one attack", 1),
            ("Piercing", "piercing", 400, 1, "Bullets pass through", 5),
            ("Lifesteal", "lifesteal", 500, 1, "Heal 0.5 health per hit", 5),
            ("Multishot+", "multishot", 150, 5, "Fire even more shots", 3),
            ("Critical Hit", "crit", 450, 1, "25% chance 2x damage", 7),
            ("Regeneration", "regen", 600, 1, "Heal 2 HP every 2s", 7),
            ("Ultra Damage", "ultradamage", 800, 10, "MASSIVE damage boost", 10),
            ("Mega Shield", "megashield", 1200, 1, "Block THREE attacks", 10),
            ("Time Slow", "timeslow", 1500, 1, "50% slower enemies", 12),
            ("Explosive", "explosive", 2000, 1, "Bullets explode on hit", 15),
            ("Vampire", "vampire", 2500, 1, "Heal 1 per hit", 15),
            ("Berserker", "berserker", 3000, 1, "2x damage under 30% HP", 20),
            ("Golden Heart", "goldenheart", 1000, 10, "+50 max HP per level", 20),
            ("Laser Null", "lasernull", 4000, 1, "50% laser dodge chance", 25),
            ("God Mode", "godmode", 10000, 1, "Start with 500 HP", 30),
            ("Reflect", "reflect", 5000, 1, "Reflect 3 attacks/level", 30),
            ("Immortal", "immortal", 25000, 1, "Survive lethal damage once", 40),
            ("Berserker Squared", "berserker_sqr", 10000, 1, "Damage ^1.5 at <10% HP", 40),
            ("Nuclear Shot", "nuclearshot", 30000, 1, "Massive explosions", 45),
            ("Infinite Ammo", "infiniteammo", 20000, 1, "No fire rate cooldown", 50),
            ("Titan Shield", "titanshield", 35000, 1, "Block FIVE attacks", 50),
            ("Voidwalker", "voidwalker", 50000, 1, "5s invincibility every 30s", 60),
            ("Parry", "parry", 2000, 1, "Reflect attacks with Spacebar", 15),
            ("Bullet Storm", "bulletstorm", 1500, 1, "Rapid-fire bullet output", 12),
            ("Homing Rounds", "homingrounds", 3500, 1, "Bullets auto-home to boss", 18),
        ]
        
        # Scroll hint
        if self.shop_scroll < 1500:
            scroll_hint = self.font_tiny.render("v Scroll for more", True, (150, 150, 150))
            self.screen.blit(scroll_hint, (320, 560))
        
        for idx, (name, key, base, max_lv, desc, req_level) in enumerate(items):
            y = 160 + idx * 75 - self.shop_scroll
            if y < -75 or y > 600:
                continue
            
            cur = self.save_data["upgrades"][key]
            locked = game_state.max_level < req_level
            
            if isinstance(cur, bool):
                owned = cur
                lv_text = "OWNED" if owned else "Buy"
                cost = base
            else:
                owned = cur >= max_lv
                lv_text = "MAX" if owned else f"Lv {cur}/{max_lv}"
                cost = base * (cur + 1)
            
            name_color = (100, 100, 100) if locked else (200, 255, 200)
            name_surf = self.font_tiny.render(name, True, name_color)
            self.screen.blit(name_surf, (40, y))
            
            if locked:
                lock_surf = self.font_tiny.render(f"Requires Lv {req_level}", True, (255, 100, 100))
                self.screen.blit(lock_surf, (40, y+22))
            else:
                lv_surf = self.font_tiny.render(lv_text, True, (180, 180, 180))
                self.screen.blit(lv_surf, (40, y+22))
            
            desc_surf = self.font_tiny.render(desc, True, (120, 120, 150))
            self.screen.blit(desc_surf, (40, y+44))
            
            can_buy = (not owned) and (game_state.coins >= cost) and (not locked)
            
            if locked:
                col = (40, 40, 40)
            elif can_buy:
                col = (0, 140, 0)
            else:
                col = (80, 40, 40)
            
            if self._button("LOCKED" if locked else f"${cost}", 550, y, 120, 50, col, (col[0]+40, col[1]+40, col[2]+40)):
                if can_buy:
                    return {"type": "buy_upgrade", "key": key, "cost": cost, "current": cur}
        
        if self._button("BACK", 300, 560, 200, 50, (150, 0, 0), (200, 0, 0)):
            return {"type": "change_state", "state": "SHOP_MENU"}
        
        return None
    
    def render_ability_temple(self, game_state, ability_manager):
        """Render ability temple with animations"""
        title = self.font_big.render("ABILITY TEMPLE", True, (200, 150, 255))
        self.screen.blit(title, (180, 40))
        
        allowed = (game_state.max_level // 10) - self.save_data.get("ability_picks_used", 0)
        
        picks_text = f"Ability Picks Remaining: {allowed}"
        picks_color = (200, 255, 200) if allowed > 0 else (255, 100, 100)
        picks_surf = self.font_small.render(picks_text, True, picks_color)
        self.screen.blit(picks_surf, (260, 100))
        
        podium_x = [150, 400, 650]
        
        for i, ability in enumerate(ability_manager.temple_choices):
            stacks = ability_manager.get_ability_stacks(ability.name)
            rarity_color = ability_manager.RARITY_COLORS.get(ability.rarity, (255, 255, 255))
            
            base_y = 360
            podium_y = base_y + math.sin(time.time() * 2 + i * 1.7) * 8
            
            # Enhanced podium
            pygame.draw.rect(self.screen, (100, 100, 150), (podium_x[i]-50, int(podium_y), 100, 20))
            pygame.draw.rect(self.screen, (150, 150, 200), (podium_x[i]-45, int(podium_y)-10, 90, 10))
            pygame.draw.rect(self.screen, (80, 80, 100), (podium_x[i]-50, int(podium_y)+20, 100, 20))
            
            float_y = 280 + math.sin(time.time() * 1.5 + i * 1.7) * 12
            
            # Pulsing glow
            glow = 100 + math.sin(time.time() * 4 + i) * 50
            pygame.draw.rect(self.screen, (*rarity_color, int(glow)), 
                           (podium_x[i]-65, int(float_y)-10, 130, 90), 3)
            
            # Ability particles
            if random.random() < 0.3:
                particle_x = podium_x[i] + random.randint(-40, 40)
                particle_y = float_y + random.randint(-20, 40)
                pygame.draw.circle(self.screen, rarity_color, (particle_x, int(particle_y)), 2)
            
            name_surf = self.font_small.render(ability.name, True, rarity_color)
            self.screen.blit(name_surf, (podium_x[i]-80, int(float_y)))
            
            stack_surf = self.font_tiny.render(f"Stacks: {stacks}", True, (200, 200, 200))
            self.screen.blit(stack_surf, (podium_x[i]-40, int(float_y)+28))
            
            desc_surf = self.font_tiny.render(ability.description, True, (160, 160, 200))
            self.screen.blit(desc_surf, (podium_x[i]-90, int(float_y)+48))
            
            select_color = (0, 150, 0) if allowed > 0 else (80, 80, 80)
            if self._button("SELECT", podium_x[i]-60, 440, 120, 40, select_color, (select_color[0]+50, select_color[1]+50, select_color[2]+50)):
                if allowed > 0:
                    return {"type": "select_ability", "ability": ability}
        
        # Roll button with cost
        roll_cost = ability_manager.get_roll_cost()
        roll_text = "FIRST ROLL FREE" if roll_cost == 0 else f"ROLL (${roll_cost})"
        can_afford = roll_cost == 0 or game_state.coins >= roll_cost
        
        roll_color = (150, 100, 200) if can_afford else (80, 40, 80)
        if self._button(roll_text, 300, 500, 200, 60, roll_color, (200, 150, 255)):
            if can_afford:
                self.rolling = True
                self.roll_start = time.time()
                return {"type": "roll_temple"}
        
        if self._button("BACK", 20, 520, 160, 50, (150, 0, 0), (200, 0, 0)):
            ability_manager.rolls_this_session = 0
            return {"type": "change_state", "state": "MENU"}
        
        return None
    
    def render_settings(self):
        """Render settings menu"""
        title = self.font_big.render("SETTINGS", True, (255, 215, 0))
        self.screen.blit(title, (270, 40))
        
        theme_label = self.font_med.render("Theme:", True, (255, 255, 255))
        self.screen.blit(theme_label, (150, 150))
        
        theme_text = "Dark Mode" if self.save_data["settings"]["theme"] == "dark" else "Light Mode"
        if self._button(theme_text, 400, 140, 200, 60, (0, 100, 200), (0, 150, 255)):
            return {"type": "toggle_theme"}
        
        move_label = self.font_med.render("Movement:", True, (255, 255, 255))
        self.screen.blit(move_label, (150, 250))
        
        move_text = "Mouse" if self.save_data["settings"]["movement"] == "mouse" else "Arrow Keys"
        if self._button(move_text, 400, 240, 200, 60, (0, 100, 200), (0, 150, 255)):
            return {"type": "toggle_movement"}
        
        cb_label = self.font_med.render("Colorblind Mode:", True, (255, 255, 255))
        self.screen.blit(cb_label, (150, 350))
        
        cb_text = "ON" if self.save_data["settings"]["colorblind"] else "OFF"
        if self._button(cb_text, 400, 340, 200, 60, (0, 100, 200), (0, 150, 255)):
            return {"type": "toggle_colorblind"}
        
        admin_text = "ON" if self.save_data["settings"]["admin"] else "OFF"
        if self._button(admin_text, 725, 550, 50, 30, (0, 100, 200), (0, 150, 255)):
            return {"type": "change_state", "state": "ADMIN_MENU"}
        
        if self._button("BACK", 300, 480, 200, 60, (150, 0, 0), (200, 0, 0)):
            return {"type": "change_state", "state": "MENU"}
        
        return None
    
    def render_admin_menu(self, admin_state):
        """Render admin password screen"""
        title = self.font_big.render("ADMIN ACCESS", True, (255, 215, 0))
        self.screen.blit(title, (230, 80))
        
        prompt = self.font_small.render("Enter password:", True, (255, 255, 255))
        self.screen.blit(prompt, (280, 180))
        
        pygame.draw.rect(self.screen, (40, 40, 40), (250, 230, 300, 50))
        pygame.draw.rect(self.screen, (255, 255, 255), (250, 230, 300, 50), 3)
        
        masked = "*" * len(self.admin_input)
        input_surf = self.font_med.render(masked, True, (255, 255, 255))
        self.screen.blit(input_surf, (260, 240))
        
        if self._button("BACK", 300, 380, 200, 60, (150, 0, 0), (200, 0, 0)):
            self.admin_input = ""
            return {"type": "change_state", "state": "SETTINGS"}
        
        return None
    
    def render_pause_menu(self):
        """Render pause overlay"""
        overlay = pygame.Surface((800, 600))
        overlay.set_alpha(128)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))
        
        paused = self.font_big.render("PAUSED", True, (255, 255, 255))
        self.screen.blit(paused, (280, 200))
        
        hint = self.font_small.render("Press ESC to resume", True, (200, 200, 200))
        self.screen.blit(hint, (260, 280))
        
        if self._button("Resume", 250, 350, 140, 60, (0, 120, 0), (0, 180, 0)):
            return {"type": "resume"}
        
        if self._button("Menu", 410, 350, 140, 60, (150, 0, 0), (200, 0, 0)):
            return {"type": "change_state", "state": "MENU"}
        
        return None
    
    def render_victory(self, game_state):
        """Render victory screen"""
        is_super = game_state.level % 10 == 0
        title_text = "SUPER BOSS DEFEATED!" if is_super else f"LEVEL {game_state.level} CLEARED!"
        title_color = (255, 0, 255) if is_super else (0, 255, 100)
        
        title_y = 200 + math.sin(time.time() * 3) * 8
        title = self.font_big.render(title_text, True, title_color)
        self.screen.blit(title, (80 if is_super else 120, int(title_y)))
        
        from game.scaling import ScalingFormulas
        coin_reward = ScalingFormulas.coin_reward(game_state.level)
        
        coins = self.font_med.render(f"+{coin_reward} coins!", True, (255, 215, 0))
        self.screen.blit(coins, (290, 280))
        
        if self._button("Continue", 200, 400, 180, 60, (0, 150, 0), (0, 200, 0)):
            return {"type": "change_state", "state": "LEVELSELECT"}
        
        if self._button("Shop", 420, 400, 180, 60, (0, 100, 200), (0, 150, 255)):
            return {"type": "change_state", "state": "SHOP_MENU"}
        
        return None
    
    def render_gameover(self, game_state):
        """Render game over screen"""
        title = self.font_big.render("GAME OVER", True, (255, 0, 0))
        self.screen.blit(title, (260, 200))
        
        level_text = self.font_small.render(f"Reached Level {game_state.level}", True, (200, 200, 200))
        self.screen.blit(level_text, (300, 260))
        
        if self._button("Retry", 200, 350, 180, 60, (150, 100, 0), (200, 150, 0)):
            return {"type": "start_level", "level": game_state.level}
        
        if self._button("Menu", 420, 350, 180, 60, (150, 0, 0), (200, 0, 0)):
            return {"type": "change_state", "state": "MENU"}
        
        return None
    
    def _button(self, text, x, y, w, h, col, hover_col):
        """Render button and return True if clicked (only once per click)"""
        mouse = pygame.mouse.get_pos()
        mouse_pressed = pygame.mouse.get_pressed()[0]
        rect = pygame.Rect(x, y, w, h)
        
        color = hover_col if rect.collidepoint(mouse) else col
        pygame.draw.rect(self.screen, color, rect)
        pygame.draw.rect(self.screen, (255, 255, 255), rect, 3)
        
        text_surf = self.font_small.render(text, True, (255, 255, 255))
        text_rect = text_surf.get_rect(center=rect.center)
        self.screen.blit(text_surf, text_rect)
        
        # Detect click: mouse pressed now but wasn't pressed last frame
        # Only process one click per frame to prevent multiple buttons triggering
        clicked = False
        if rect.collidepoint(mouse) and mouse_pressed and not self.mouse_was_pressed and not self.frame_click_processed:
            clicked = True
            self.frame_click_processed = True  # Mark that we've processed a click this frame
        
        # Note: mouse_was_pressed is updated at the end of render functions, not here
        return clicked

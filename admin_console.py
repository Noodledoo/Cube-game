"""
FILE: game/admin_console.py
Professional developer console with autocomplete and history
"""

import pygame
from typing import List, Dict, Callable, Optional
from dataclasses import dataclass

@dataclass
class ConsoleCommand:
    """Command definition for autocomplete"""
    name: str
    args: List[str]
    description: str
    
    def get_signature(self) -> str:
        """Get command signature"""
        args_str = " ".join(f"<{arg}>" for arg in self.args)
        return f"{self.name} {args_str}".strip()

class AdminConsole:
    """Developer console with autocomplete and history"""
    
    def __init__(self, width: int = 800, height: int = 300):
        self.width = width
        self.height = height
        self.visible = False
        
        # Input
        self.input_text = ""
        self.cursor_pos = 0
        self.cursor_blink_timer = 0.0
        
        # History
        self.command_history: List[str] = []
        self.output_history: List[tuple] = []
        self.history_index = -1
        self.max_history = 100
        self.max_output = 200
        
        # Scrolling
        self.scroll_offset = 0
        
        # Autocomplete
        self.suggestions: List[ConsoleCommand] = []
        self.suggestion_index = 0
        
        # Styling
        self.bg_color = (20, 20, 30, 230)
        self.text_color = (200, 255, 200)
        self.input_color = (255, 255, 255)
        self.suggestion_color = (150, 150, 200)
        self.error_color = (255, 100, 100)
        
        self.font = pygame.font.Font(None, 20)
        self.line_height = 22
        
        # Command registry
        self.commands: Dict[str, ConsoleCommand] = {}
        self._register_default_commands()
        
        # Callback for command execution
        self.execute_callback: Optional[Callable] = None
        
        # Save data reference for admin commands
        self.save_data: Optional[dict] = None
    
    def _register_default_commands(self):
        """Register all available commands"""
        commands = [
            ConsoleCommand("help", [], "Show all commands"),
            ConsoleCommand("clear", [], "Clear console output"),
            ConsoleCommand("setplayerstat", ["stat", "value"], "Set player stat (dmg|speed|firerate)"),
            ConsoleCommand("healplayer", ["amount?"], "Heal player"),
            ConsoleCommand("killplayer", [], "Kill player instantly"),
            ConsoleCommand("makeplayerinvincible", ["true|false"], "Toggle invincibility"),
            ConsoleCommand("givemoney", ["amount"], "Add coins"),
            ConsoleCommand("setmoney", ["amount"], "Set coins to exact amount"),
            ConsoleCommand("makemerich", [], "Add 999999 coins"),
            ConsoleCommand("setlevel", ["level"], "Jump to level"),
            ConsoleCommand("killboss", [], "Instantly kill boss"),
            ConsoleCommand("skiplevel", [], "Complete current level"),
            ConsoleCommand("showstats", ["true|false"], "Toggle stats overlay"),
            ConsoleCommand("framestep", ["true|false"], "Enable frame-by-frame mode"),
            ConsoleCommand("step", [], "Advance one frame"),
            ConsoleCommand("timescale", ["scale"], "Set game speed (0.1 - 5.0)"),
            ConsoleCommand("addbot", ["name?"], "Add a bot player"),
            ConsoleCommand("removebot", ["id?"], "Remove a bot player"),
            ConsoleCommand("botcount", [], "Show number of bots"),
            ConsoleCommand("listbots", [], "List all bot players"),
        ]
        
        for cmd in commands:
            self.commands[cmd.name] = cmd
    
    def set_execute_callback(self, callback: Callable):
        """Set callback for command execution"""
        self.execute_callback = callback
    
    def set_save_data(self, save_data: dict):
        """Set save data reference for admin commands"""
        self.save_data = save_data
    
    def try_toggle(self) -> bool:
        """Try to toggle console visibility. Returns True if toggled."""
        self.visible = not self.visible
        return True
    
    def update(self, dt: float):
        """Update console state"""
        if not self.visible:
            return
        
        self.cursor_blink_timer += dt
    
    def handle_event(self, event: pygame.event) -> bool:
        """Handle input events. Returns True if event was consumed."""
        if not self.visible:
            return False
        
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self._execute_command()
                return True
            
            elif event.key == pygame.K_BACKSPACE:
                if self.input_text and self.cursor_pos > 0:
                    self.input_text = (self.input_text[:self.cursor_pos-1] + 
                                      self.input_text[self.cursor_pos:])
                    self.cursor_pos -= 1
                    self._update_suggestions()
                return True
            
            elif event.key == pygame.K_DELETE:
                if self.cursor_pos < len(self.input_text):
                    self.input_text = (self.input_text[:self.cursor_pos] + 
                                      self.input_text[self.cursor_pos+1:])
                    self._update_suggestions()
                return True
            
            elif event.key == pygame.K_LEFT:
                self.cursor_pos = max(0, self.cursor_pos - 1)
                return True
            
            elif event.key == pygame.K_RIGHT:
                self.cursor_pos = min(len(self.input_text), self.cursor_pos + 1)
                return True
            
            elif event.key == pygame.K_UP:
                self._history_up()
                return True
            
            elif event.key == pygame.K_DOWN:
                self._history_down()
                return True
            
            elif event.key == pygame.K_TAB:
                self._autocomplete()
                return True
            
            elif event.unicode and event.unicode.isprintable():
                self.input_text = (self.input_text[:self.cursor_pos] + 
                                  event.unicode + 
                                  self.input_text[self.cursor_pos:])
                self.cursor_pos += 1
                self._update_suggestions()
                return True
        
        elif event.type == pygame.MOUSEWHEEL:
            self.scroll_offset = max(0, self.scroll_offset - event.y * 3)
            return True
        
        return False
    
    def _execute_command(self):
        """Execute the current input command"""
        if not self.input_text.strip():
            return
        
        # Add to history
        self.command_history.append(self.input_text)
        if len(self.command_history) > self.max_history:
            self.command_history.pop(0)
        
        self.log(f"> {self.input_text}", self.input_color)
        
        # Clear input
        command = self.input_text
        self.input_text = ""
        self.cursor_pos = 0
        self.history_index = -1
        self.suggestions = []
        
        # Special commands
        if command.lower() == "clear":
            self.output_history.clear()
            self.scroll_offset = 0
            return
        
        if command.lower() == "help":
            self._show_help()
            return
        
        # Execute via callback
        if self.execute_callback:
            result = self.execute_callback(command)
            if result:
                self.log(result, self.text_color)
        else:
            self.log(f"Command: {command}", self.suggestion_color)
    
    def _show_help(self):
        """Show all available commands"""
        self.log("Available commands:", self.text_color)
        for cmd in sorted(self.commands.values(), key=lambda x: x.name):
            self.log(f"  {cmd.get_signature()}", self.suggestion_color)
            self.log(f"    {cmd.description}", self.text_color)
    
    def _history_up(self):
        """Navigate command history backwards"""
        if not self.command_history:
            return
        
        if self.history_index == -1:
            self.history_index = len(self.command_history) - 1
        else:
            self.history_index = max(0, self.history_index - 1)
        
        self.input_text = self.command_history[self.history_index]
        self.cursor_pos = len(self.input_text)
        self._update_suggestions()
    
    def _history_down(self):
        """Navigate command history forwards"""
        if self.history_index == -1:
            return
        
        self.history_index += 1
        if self.history_index >= len(self.command_history):
            self.history_index = -1
            self.input_text = ""
        else:
            self.input_text = self.command_history[self.history_index]
        
        self.cursor_pos = len(self.input_text)
        self._update_suggestions()
    
    def _update_suggestions(self):
        """Update autocomplete suggestions"""
        if not self.input_text:
            self.suggestions = []
            self.suggestion_index = 0
            return
        
        prefix = self.input_text.split()[0].lower()
        self.suggestions = [
            cmd for name, cmd in self.commands.items()
            if name.startswith(prefix)
        ][:5]
        self.suggestion_index = 0
    
    def _autocomplete(self):
        """Complete current input with suggestion"""
        if not self.suggestions:
            return
        
        # Get current suggestion
        suggestion = self.suggestions[self.suggestion_index]
        self.input_text = suggestion.name
        self.cursor_pos = len(self.input_text)
        
        # Move to next suggestion for next tab press
        self.suggestion_index = (self.suggestion_index + 1) % len(self.suggestions)
    
    def log(self, message: str, color=None):
        """Add message to output history"""
        if color is None:
            color = self.text_color
        
        self.output_history.append((message, color))
        if len(self.output_history) > self.max_output:
            self.output_history.pop(0)
        
        # Auto-scroll to bottom
        self.scroll_offset = max(0, len(self.output_history) * self.line_height - self.height + 60)
    
    def render(self, screen: pygame.Surface):
        """Render console"""
        if not self.visible:
            return
        
        # Background
        console_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        console_surface.fill(self.bg_color)
        
        # Output history
        y = 10 - self.scroll_offset
        for message, color in self.output_history:
            if y > -self.line_height and y < self.height - 50:
                text = self.font.render(message, True, color)
                console_surface.blit(text, (10, y))
            y += self.line_height
        
        # Input area separator
        pygame.draw.line(console_surface, (100, 100, 100), 
                        (0, self.height - 45), (self.width, self.height - 45), 2)
        
        # Input prompt
        prompt = self.font.render(">", True, self.input_color)
        console_surface.blit(prompt, (10, self.height - 35))
        
        # Input text
        input_surface = self.font.render(self.input_text, True, self.input_color)
        console_surface.blit(input_surface, (30, self.height - 35))
        
        # Cursor
        if int(self.cursor_blink_timer * 2) % 2 == 0:
            cursor_x = 30 + self.font.size(self.input_text[:self.cursor_pos])[0]
            pygame.draw.line(console_surface, self.input_color,
                           (cursor_x, self.height - 35),
                           (cursor_x, self.height - 15), 2)
        
        # Autocomplete suggestions
        if self.suggestions:
            suggestion_y = self.height - 70
            for i, suggestion in enumerate(self.suggestions[:3]):
                color = self.suggestion_color if i != self.suggestion_index % len(self.suggestions) else (255, 255, 150)
                text = self.font.render(f"  {suggestion.get_signature()}", True, color)
                console_surface.blit(text, (10, suggestion_y))
                suggestion_y -= self.line_height
        
        # Blit to screen
        screen.blit(console_surface, (0, 0))

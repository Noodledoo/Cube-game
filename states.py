"""
FILE: game/states.py
Complete game state dataclasses
"""

from dataclasses import dataclass, field
from typing import List

@dataclass
class GameState:
    """Master game state - controls flow"""
    level: int = 1
    coins: int = 0
    max_level: int = 1
    paused: bool = False
    time_scale: float = 1.0
    screen_state: str = "MENU"  # MENU, GAME, SHOP, LEVELSELECT, SHOP_MENU, ABILITY_TEMPLE, SETTINGS, ADMIN_MENU, VICTORY, GAMEOVER, MULTIPLAYER_MENU, MULTIPLAYER_LOBBY, PVP_LOBBY
    frame_count: int = 0
    game_time: float = 0.0
    
    def update(self, dt: float):
        """Update game time with time scaling"""
        self.game_time += dt * self.time_scale
        self.frame_count += 1

@dataclass
class PlayerState:
    """Player stats and state"""
    x: float = 400.0
    y: float = 300.0
    hp: float = 100.0
    max_hp: float = 100.0
    
    # Base stats
    base_damage: float = 5.0
    base_speed: float = 400.0
    base_fire_rate: float = 0.35
    
    # Status effects
    invincible: bool = False
    invisible: bool = False
    berserker_active: bool = False
    time_frozen: bool = False
    parry_active: bool = False
    parry_duration: float = 0.0
    
    # Shields
    shield_active: bool = False
    mega_shield_active: bool = False
    titan_shield_active: bool = False
    reflect_charges: int = 0
    
    # Timers
    last_shot: float = 0.0
    invincible_timer: float = 0.0
    voidwalker_timer: float = 0.0
    regen_timer: float = 0.0
    
    # Multiplayer
    player_id: int = 0
    player_name: str = "Player"
    
    def update(self, dt: float):
        """Update player state"""
        if self.invincible_timer > 0:
            self.invincible_timer -= dt
            self.invincible = self.invincible_timer > 0
        
        if self.parry_active:
            self.parry_duration -= dt
            if self.parry_duration <= 0:
                self.parry_active = False

@dataclass
class BossState:
    """Boss stats and AI state"""
    x: float = 400.0
    y: float = 300.0
    hp: float = 500.0
    max_hp: float = 500.0
    phase: int = 0
    
    # AI state
    charging: bool = False
    charge_timer: float = 0.0
    charge_duration: float = 1.5
    charge_dir: List[float] = field(default_factory=lambda: [0.0, 0.0])
    charge_speed: float = 0.0
    returning_to_center: bool = False
    
    # Attack timers
    last_laser: float = 0.0
    last_charge: float = 0.0
    last_wave: float = 0.0
    last_spiral: float = 0.0
    last_homing: float = 0.0
    last_rapid: float = 0.0
    last_spray: float = 0.0
    last_chasing: float = 0.0
    
    emotion: str = "normal"  # normal, angry, charging, hurt, super
    
    def get_hp_percent(self) -> float:
        return self.hp / self.max_hp if self.max_hp > 0 else 0
    
    def update(self, dt: float, game_level: int):
        """Update boss state"""
        if self.charging:
            self.charge_timer += dt
            if self.charge_timer >= self.charge_duration:
                self.charging = False
                self.charge_timer = 0.0
        
        # Update emotion based on HP
        hp_pct = self.get_hp_percent()
        is_super = game_level % 10 == 0
        
        if is_super:
            self.emotion = "super"
        elif self.charging:
            self.emotion = "charging"
        elif hp_pct < 0.3:
            self.emotion = "angry"
        else:
            self.emotion = "normal"

@dataclass
class AdminState:
    """Admin/debug mode state"""
    enabled: bool = False
    password: str = "ilovenoodledoo"
    console_open: bool = False
    console_history: List[str] = field(default_factory=list)
    console_input: str = ""
    
    # Flags
    free_shop: bool = False
    show_stats: bool = False
    show_hitboxes: bool = False
    show_heatmap: bool = False
    frame_step_mode: bool = False
    can_step: bool = False
    
    def execute_command(self, cmd: str, game_state: 'GameState', 
                       player_state: 'PlayerState', boss_state: 'BossState',
                       save_data: dict, ability_manager):
        """Execute admin command"""
        parts = cmd.strip().split()
        if not parts:
            return "No command"
        
        command = parts[0].lower()
        
        try:
            # Player commands
            if command == "setplayerstat":
                stat = parts[1].lower()
                value = float(parts[2])
                if stat == "dmg":
                    save_data["upgrades"]["damage"] = int(value)
                elif stat == "speed":
                    save_data["upgrades"]["speed"] = int(value)
                elif stat == "firerate":
                    save_data["upgrades"]["firerate"] = int(value)
                return f"Set {stat} to {value}"
            
            elif command == "healplayer":
                amount = float(parts[1]) if len(parts) > 1 else player_state.max_hp
                player_state.hp = min(player_state.hp + amount, player_state.max_hp)
                return f"Healed {amount} HP"
            
            elif command == "killplayer":
                player_state.hp = 0
                return "Player killed"
            
            elif command == "makeplayerinvincible":
                value = parts[1].lower() == "true" if len(parts) > 1 else True
                player_state.invincible = value
                player_state.invincible_timer = 999999 if value else 0
                return f"Invincible: {value}"
            
            # Economy commands
            elif command == "givemoney":
                amount = int(parts[1])
                game_state.coins += amount
                save_data["coins"] = game_state.coins
                return f"Added {amount} coins"
            
            elif command == "setmoney":
                amount = int(parts[1])
                game_state.coins = amount
                save_data["coins"] = game_state.coins
                return f"Set coins to {amount}"
            
            elif command == "makemerich":
                game_state.coins += 999999
                save_data["coins"] = game_state.coins
                return "Made rich!"
            
            # Game control
            elif command == "setlevel":
                level = int(parts[1])
                game_state.level = level
                return f"Set level to {level}"
            
            elif command == "killboss":
                boss_state.hp = 0
                return "Boss killed"
            
            elif command == "skiplevel":
                game_state.level += 1
                game_state.max_level = max(game_state.max_level, game_state.level)
                save_data["max_level"] = game_state.max_level
                return f"Skipped to level {game_state.level}"
            
            # Debug commands
            elif command == "showstats":
                value = parts[1].lower() == "true" if len(parts) > 1 else not self.show_stats
                self.show_stats = value
                return f"Show stats: {value}"
            
            elif command == "framestep":
                value = parts[1].lower() == "true" if len(parts) > 1 else not self.frame_step_mode
                self.frame_step_mode = value
                self.can_step = False
                return f"Frame step mode: {value}"
            
            elif command == "step":
                if self.frame_step_mode:
                    self.can_step = True
                    return "Stepping one frame"
                return "Not in frame step mode"
            
            elif command == "timescale":
                scale = float(parts[1])
                game_state.time_scale = max(0.1, min(5.0, scale))
                return f"Time scale: {game_state.time_scale}"
            
            # Bot commands
            elif command == "addbot":
                return "Bot added (requires server)"
            
            elif command == "removebot":
                return "Bot removed (requires server)"
            
            elif command == "botcount":
                return "Bot count: 0 (requires server)"
            
            elif command == "help":
                return "Commands: setplayerstat, healplayer, givemoney, setlevel, killboss, showstats, framestep, step, timescale, addbot, removebot"
            
            else:
                return f"Unknown command: {command}"
        
        except Exception as e:
            return f"Error: {str(e)}"

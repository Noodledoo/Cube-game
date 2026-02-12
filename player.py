"""
FILE: game/player.py
Complete player movement, shooting, and abilities - FIXED VERSION
Fixes:
- Homing bullets no longer orbit boss (dynamic turn rate + distance check)
- Piercing bullets track "has_hit_boss" to prevent re-homing
"""

import pygame
import math
import time
import random
from scaling import ScalingFormulas

class Player:
    """Player controller with all abilities"""
    
    def __init__(self, player_state, save_data, ability_manager, animation_manager):
        self.player_state = player_state
        self.save_data = save_data
        self.ability_manager = ability_manager
        self.animation_manager = animation_manager
        
        self.projectiles = []
    
    def update(self, dt, level, boss_state):
        """Update player state"""
        # Movement
        self._update_movement(dt)
        
        # Abilities
        self._update_abilities(dt, boss_state)
        
        # Shooting
        self._update_shooting(dt, level, boss_state)
        
        # Update projectiles
        self._update_projectiles(dt, boss_state)
        
        # Voidwalker timer
        if self.save_data["upgrades"]["voidwalker"]:
            self.player_state.voidwalker_timer += dt
            if self.player_state.voidwalker_timer >= 30:
                self.player_state.voidwalker_timer = 0
        
        # Regeneration
        if self.save_data["upgrades"]["regen"]:
            self.player_state.regen_timer += dt
            if self.player_state.regen_timer >= 2:
                self.player_state.hp = min(self.player_state.hp + 2, self.player_state.max_hp)
                self.player_state.regen_timer = 0
        
        # Berserker check
        self.player_state.berserker_active = (
            self.save_data["upgrades"]["berserker"] and 
            self.player_state.hp < self.player_state.max_hp * 0.3
        )
        
        # Recalculate max HP to account for real-time ability changes (chaos_bargain)
        hp_bonus = (self.save_data["upgrades"]["health"] - 1) * 25
        golden_bonus = (self.save_data["upgrades"]["goldenheart"] - 1) * 50
        chaos_penalty = self.save_data["abilities"].get("chaos_bargain", 0) * 5
        new_max_hp = 100 + hp_bonus + golden_bonus - chaos_penalty

        # God mode check
        if self.save_data["upgrades"]["godmode"] and new_max_hp < 500:
            new_max_hp = 500

        if new_max_hp != self.player_state.max_hp:
            self.player_state.max_hp = new_max_hp
            self.player_state.hp = min(self.player_state.hp, self.player_state.max_hp)
    
    def _update_movement(self, dt):
        """Update player movement"""
        speed = 400
        
        if self.save_data["settings"]["movement"] == "mouse":
            mx, my = pygame.mouse.get_pos()
            self.player_state.x = float(mx)
            self.player_state.y = float(my)
        else:
            keys = pygame.key.get_pressed()
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                self.player_state.x -= speed * dt
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                self.player_state.x += speed * dt
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                self.player_state.y -= speed * dt
            if keys[pygame.K_DOWN] or keys[pygame.K_s]:
                self.player_state.y += speed * dt
            
            self.player_state.x = max(20, min(780, self.player_state.x))
            self.player_state.y = max(20, min(580, self.player_state.y))
        
        # Add trail
        self.animation_manager.add_trail(self.player_state.x, self.player_state.y)
    
    def _update_abilities(self, dt, boss_state):
        """Update and trigger abilities"""
        now = time.time()
        keys = pygame.key.get_pressed()
        
        for ability_name, ability in self.ability_manager.player_abilities.items():
            if ability.key is None:
                continue
            
            if keys[ability.key] and self.ability_manager.can_use_ability(ability_name, now):
                self._trigger_ability(ability_name, ability, boss_state)
                self.ability_manager.use_ability(ability_name, now)
    
    def _trigger_ability(self, name, ability, boss_state):
        """Trigger specific ability"""
        if name == "teleport":
            self.animation_manager.trigger_teleport(self.player_state.x, self.player_state.y)
            self.player_state.x = 800 - self.player_state.x
            self.player_state.y = 600 - self.player_state.y
            self.animation_manager.trigger_teleport(self.player_state.x, self.player_state.y)
            # Stacking grants brief invincibility after teleport
            if ability.stacks >= 2:
                i_frames = 0.3 + (ability.stacks - 2) * 0.15  # 0.3s at 2 stacks, up to 0.75s at 5
                self.player_state.invincible = True
                self.player_state.invincible_timer = i_frames
        
        elif name == "dash":
            # Dash away from boss
            dx = self.player_state.x - boss_state.x
            dy = self.player_state.y - boss_state.y
            length = math.hypot(dx, dy)
            if length > 0:
                dash_dist = 150 + ability.stacks * 20
                self.player_state.x += (dx / length) * dash_dist
                self.player_state.y += (dy / length) * dash_dist
                self.player_state.x = max(20, min(780, self.player_state.x))
                self.player_state.y = max(20, min(580, self.player_state.y))
                self.animation_manager.screen_shake(6, 0.2)
                for _ in range(10):
                    self.animation_manager.spawn_particle(
                        self.player_state.x, self.player_state.y, 
                        (150, 200, 255), 20, 
                        (random.uniform(-3, 3), random.uniform(-3, 3))
                    )
        
        elif name == "shockwave":
            radius = 200 + ability.stacks * 30
            self.animation_manager.spawn("explosion", 
                                        self.player_state.x, 
                                        self.player_state.y, 
                                        lifetime=0.3, 
                                        max_radius=radius, 
                                        color=(255, 255, 0))
            self.animation_manager.screen_shake(10, 0.3)
        
        elif name == "timeshatter":
            # Visual effect only - time freeze handled in main
            self.animation_manager.screen_shake(4, 0.3)
            for _ in range(30):
                angle = random.uniform(0, 2 * math.pi)
                speed = random.uniform(2, 6)
                self.animation_manager.spawn_particle(
                    self.player_state.x, self.player_state.y,
                    (100, 200, 255), 40,
                    (math.cos(angle) * speed, math.sin(angle) * speed)
                )
    
    def _update_shooting(self, dt, level, boss_state):
        """Handle player shooting"""
        now = time.time()
        
        # Calculate fire rate
        cd = max(0.08, 0.35 - (self.save_data["upgrades"]["firerate"] - 1) * 0.07)
        if self.save_data["upgrades"]["rapid"]:
            cd *= 0.5
        if self.save_data["upgrades"]["bulletstorm"]:
            cd *= 0.35
        if self.save_data["upgrades"]["infiniteammo"]:
            cd = 0.02
        
        if pygame.mouse.get_pressed()[0] and now - self.player_state.last_shot > cd:
            self._fire_projectile(level, boss_state)
            self.player_state.last_shot = now
    
    def _fire_projectile(self, level, boss_state):
        """Fire player projectiles"""
        angle = math.atan2(boss_state.y - self.player_state.y, boss_state.x - self.player_state.x)
        
        # Calculate damage
        base_dmg = 5 * self.save_data["upgrades"]["damage"]
        ultra_bonus = 20 * (self.save_data["upgrades"]["ultradamage"] - 1)
        level_bonus = ScalingFormulas.player_damage_bonus(level)
        chaos_bonus = self.ability_manager.get_ability_stacks("chaos_bargain") * 10
        
        dmg = base_dmg + ultra_bonus + level_bonus + chaos_bonus
        
        if self.player_state.berserker_active:
            dmg *= 2
        
        if self.save_data["upgrades"]["berserker_sqr"] and self.player_state.hp < self.player_state.max_hp * 0.1:
            dmg = dmg ** 1.5
        
        if self.save_data["upgrades"]["crit"] and time.time() % 0.25 < 0.06:  # 25% chance
            dmg *= 2
        
        base_speed = 700 + (self.save_data["upgrades"]["speed"] - 1) * 100
        
        # Multi-shot
        shots = []
        if self.save_data["upgrades"]["triple"]:
            multishot = self.save_data["upgrades"]["multishot"]
            if multishot >= 5:
                shots = [-0.8, -0.6, -0.4, -0.2, 0, 0.2, 0.4, 0.6, 0.8]
            elif multishot >= 4:
                shots = [-0.7, -0.5, -0.3, -0.1, 0, 0.1, 0.3, 0.5, 0.7]
            elif multishot >= 3:
                shots = [-0.6, -0.4, -0.2, 0, 0.2, 0.4, 0.6]
            elif multishot >= 2:
                shots = [-0.5, -0.25, 0, 0.25, 0.5]
            else:
                shots = [-0.3, 0, 0.3]
        else:
            shots = [0]
        
        for offset in shots:
            self.projectiles.append({
                "x": self.player_state.x,
                "y": self.player_state.y,
                "vx": math.cos(angle + offset) * base_speed,
                "vy": math.sin(angle + offset) * base_speed,
                "dmg": dmg,
                "piercing": self.save_data["upgrades"]["piercing"],
                "explosive": self.save_data["upgrades"]["explosive"],
                "nuclear": self.save_data["upgrades"]["nuclearshot"],
                "homing": self.save_data["upgrades"]["homingrounds"],
                "has_hit_boss": False  # FIX: Track if bullet has hit boss
            })
    
    def _update_projectiles(self, dt, boss_state):
        """Update all player projectiles - FIXED VERSION"""
        for proj in self.projectiles[:]:
            # FIX: Improved homing behavior
            if proj.get("homing") and not proj.get("has_hit_boss"):
                dx = boss_state.x - proj["x"]
                dy = boss_state.y - proj["y"]
                dist = math.hypot(dx, dy)
                
                # FIX: Only home if not too close to boss (prevents orbiting)
                if dist > 40:  # Minimum distance threshold
                    current_angle = math.atan2(proj["vy"], proj["vx"])
                    target_angle = math.atan2(dy, dx)
                    angle_diff = target_angle - current_angle
                    
                    # Normalize angle
                    while angle_diff > math.pi:
                        angle_diff -= 2 * math.pi
                    while angle_diff < -math.pi:
                        angle_diff += 2 * math.pi
                    
                    # FIX: Dynamic turn rate - faster when far, slower when close
                    # This prevents the tight orbiting behavior
                    base_turn_rate = 0.25  # Increased from 0.08
                    if dist < 100:
                        # Reduce turn rate when close to prevent orbiting
                        turn_rate = base_turn_rate * (dist / 100)
                    else:
                        turn_rate = base_turn_rate
                    
                    current_angle += angle_diff * turn_rate
                    speed = math.hypot(proj["vx"], proj["vy"])
                    proj["vx"] = math.cos(current_angle) * speed
                    proj["vy"] = math.sin(current_angle) * speed
            
            proj["x"] += proj["vx"] * dt
            proj["y"] += proj["vy"] * dt
            
            if not (0 <= proj["x"] <= 800 and 0 <= proj["y"] <= 600):
                self.projectiles.remove(proj)
    
    def activate_parry(self):
        """Activate parry"""
        if self.save_data["upgrades"]["parry"]:
            self.player_state.parry_active = True
            self.player_state.parry_duration = 0.35
    
    def clear_projectiles(self):
        """Clear all projectiles"""
        self.projectiles.clear()

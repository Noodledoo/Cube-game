"""
FILE: game/boss_ai.py
Complete Boss AI with all attack patterns - FIXED VERSION
Fixes:
- Boss lasers now fire more frequently and independently of spray
- Spray attack no longer chains infinitely at high levels
"""

import math
import time
import random
from game.scaling import ScalingFormulas

class BossAI:
    """Boss behavior and all attack patterns"""
    
    def __init__(self, boss_state, animation_manager):
        self.boss_state = boss_state
        self.animation_manager = animation_manager
        
        # Projectiles
        self.lasers = []
        self.homing_missiles = []
        self.spiral_lasers = []
        self.spray_bullets = []
        self.chasing_laser = None
        
        # Boss charging animation
        self.boss_charging_ability = False
        self.charge_start_time = 0
        self.charge_duration = 1.5
        
        # FIX: Spray attack lockout to prevent chaining
        self.spray_lockout_until = 0
    
    def reset(self, level):
        """Reset boss AI for new level"""
        self.clear_all_projectiles()
        now = time.time()
        self.boss_state.last_laser = now
        self.boss_state.last_charge = now
        self.boss_state.last_wave = now
        self.boss_state.last_spiral = now
        self.boss_state.last_homing = now
        self.boss_state.last_rapid = now
        self.boss_state.last_spray = now
        self.boss_state.last_chasing = now
        self.boss_charging_ability = False
        self.spray_lockout_until = 0
    
    def clear_all_projectiles(self):
        """Clear all boss projectiles"""
        self.lasers.clear()
        self.homing_missiles.clear()
        self.spiral_lasers.clear()
        self.spray_bullets.clear()
        self.chasing_laser = None
    
    def update(self, dt, level, player_state, time_freeze_active=False):
        """Update boss AI"""
        now = time.time()
        
        # Apply time slow
        game_dt = dt
        
        # Update projectile movement
        self._update_projectiles(game_dt, player_state.x, player_state.y)
        
        # Boss movement
        self._update_movement(game_dt, level, player_state)
        
        # Attack patterns (skip if time frozen)
        if not time_freeze_active:
            self._trigger_attacks(game_dt, level, player_state, now)
    
    def _update_projectiles(self, dt, px, py):
        """Update all projectiles"""
        # Regular lasers
        for laser in self.lasers[:]:
            laser["x"] += laser["vx"] * dt
            laser["y"] += laser["vy"] * dt
            if not (0 <= laser["x"] <= 800 and 0 <= laser["y"] <= 800):
                self.lasers.remove(laser)
        
        # Homing missiles
        for missile in self.homing_missiles[:]:
            dx = px - missile["x"]
            dy = py - missile["y"]
            target_angle = math.atan2(dy, dx)
            angle_diff = target_angle - missile["angle"]
            while angle_diff > math.pi:
                angle_diff -= 2 * math.pi
            while angle_diff < -math.pi:
                angle_diff += 2 * math.pi
            missile["angle"] += angle_diff * 0.05
            missile["x"] += math.cos(missile["angle"]) * missile["speed"] * dt
            missile["y"] += math.sin(missile["angle"]) * missile["speed"] * dt
            if not (0 <= missile["x"] <= 800 and 0 <= missile["y"] <= 800):
                self.homing_missiles.remove(missile)
        
        # Spiral lasers
        for spiral in self.spiral_lasers[:]:
            spiral["angle"] += spiral["rot_speed"] * dt
            spiral["x"] += math.cos(spiral["angle"]) * spiral["speed"] * dt
            spiral["y"] += math.sin(spiral["angle"]) * spiral["speed"] * dt
            if not (0 <= spiral["x"] <= 800 and 0 <= spiral["y"] <= 800):
                self.spiral_lasers.remove(spiral)
        
        # Spray bullets
        if len(self.spray_bullets) > 0:
            spray = self.spray_bullets[0]
            elapsed = time.time() - spray["start_time"]
            if elapsed < spray["duration"]:
                if time.time() >= spray["delay_end"]:
                    spray["angle"] += spray["rotation_speed"] * dt
                    spray["gap_angle"] += 1.2 * dt
                    
                    # Generate spray bullets each frame
                    gap_size = math.radians(35)
                    bullet_count = min(20, 16 + spray["level"] // 15)
                    
                    for i in range(bullet_count):
                        angle = (i / bullet_count) * 2 * math.pi + spray["angle"]
                        angle_diff = angle - spray["gap_angle"] - 10
                        while angle_diff > math.pi:
                            angle_diff -= 2 * math.pi
                        while angle_diff < -math.pi:
                            angle_diff += 2 * math.pi
                        if abs(angle_diff) < gap_size:
                            continue
                        
                        self.lasers.append({
                            "x": self.boss_state.x, 
                            "y": self.boss_state.y, 
                            "vx": math.cos(angle) * ScalingFormulas.projectile_speed(spray["level"], 400), 
                            "vy": math.sin(angle) * ScalingFormulas.projectile_speed(spray["level"], 400)
                        })
            else:
                if time.time() >= spray["grace_period_end"]:
                    self.spray_bullets.pop(0)
        
        # Chasing laser
        if self.chasing_laser:
            elapsed = time.time() - self.chasing_laser["start_time"]
            if elapsed < self.chasing_laser["duration"]:
                self.chasing_laser["angle"] += self.chasing_laser["rot_speed"] * dt
            else:
                self.chasing_laser = None
    
    def _update_movement(self, dt, level, player_state):
        """Update boss movement"""
        if self.boss_state.returning_to_center:
            self.boss_state.charging = False
            dx = 400 - self.boss_state.x
            dy = 300 - self.boss_state.y
            dist = math.hypot(dx, dy)
            if dist < 8:
                self.boss_state.x = 400
                self.boss_state.y = 300
                self.boss_state.returning_to_center = False
            else:
                speed = 700 + math.log(level + 1) * 150
                self.boss_state.x += (dx / dist) * speed * dt
                self.boss_state.y += (dy / dist) * speed * dt
        
        elif self.boss_state.charging:
            self.boss_state.x += self.boss_state.charge_dir[0] * self.boss_state.charge_speed * dt
            self.boss_state.y += self.boss_state.charge_dir[1] * self.boss_state.charge_speed * dt
            
            # Check bounds
            boss_r = 60
            if not (boss_r <= self.boss_state.x <= 800 - boss_r and boss_r <= self.boss_state.y <= 600 - boss_r):
                self.boss_state.charging = False
                self.boss_state.returning_to_center = True
    
    def _trigger_attacks(self, dt, level, player_state, now):
        """Trigger attack patterns"""
        px, py = player_state.x, player_state.y
        dx = px - self.boss_state.x
        dy = py - self.boss_state.y
        
        spray_active = len(self.spray_bullets) > 0
        is_super = level % 10 == 0
        
        # FIX: Basic lasers - fire more frequently and INDEPENDENTLY of spray
        # Early game: faster laser frequency (1.5s for levels 1-5)
        if level <= 5:
            laser_cd = 1.5
        else:
            laser_cd = ScalingFormulas.boss_fire_delay(level, 2.0, 0.5)  # Reduced from 2.5, min 0.5
        
        if now - self.boss_state.last_laser > laser_cd:
            # FIX: Allow lasers during spray but reduce count
            count = 3 if level < 3 else 5 if level < 10 else min(12, 7 + level // 12)
            if spray_active:
                count = max(2, count // 2)  # Reduced during spray but still fires
            
            spread = 30 if level < 4 else 45 if level < 15 else min(90, 60 + level)
            base_angle = math.atan2(dy, dx)
            
            for i in range(count):
                if count > 1:
                    a = base_angle + (i/(count-1) - 0.5) * math.radians(spread * 2)
                else:
                    a = base_angle
                self.lasers.append({
                    "x": self.boss_state.x,
                    "y": self.boss_state.y,
                    "vx": math.cos(a) * ScalingFormulas.projectile_speed(level, 400),
                    "vy": math.sin(a) * ScalingFormulas.projectile_speed(level, 400)
                })
            self.boss_state.last_laser = now
        
        # Charge attack
        charge_cd = ScalingFormulas.boss_fire_delay(level, 7.0, 2.0)
        if not self.boss_state.charging and now - self.boss_state.last_charge > charge_cd and not spray_active:
            self.boss_state.charging = True
            self.boss_state.returning_to_center = False
            dir_x = px - self.boss_state.x
            dir_y = py - self.boss_state.y
            length = math.hypot(dir_x, dir_y)
            if length > 0:
                self.boss_state.charge_dir = [dir_x / length, dir_y / length]
                self.boss_state.charge_speed = 600 + math.log(level + 1) * 180
                self.boss_state.emotion = "charging"
                self.animation_manager.spawn("charge_warning", self.boss_state.x, self.boss_state.y, lifetime=1.0)
            self.boss_state.last_charge = now
        
        # Homing missiles (level 8+)
        if level >= 8:
            homing_cd = ScalingFormulas.boss_fire_delay(level, 6.0, 2.5)
            if now - self.boss_state.last_homing > homing_cd and not spray_active:
                count = 2 if level < 15 else 3 if level < 25 else min(8, 4 + level // 20)
                for _ in range(count):
                    angle = math.radians(random.randint(0, 360))
                    self.homing_missiles.append({
                        "x": self.boss_state.x,
                        "y": self.boss_state.y,
                        "angle": angle,
                        "speed": ScalingFormulas.projectile_speed(level, 200)
                    })
                self.boss_state.last_homing = now
        
        # Spiral lasers (level 20+)
        if level >= 20:
            spiral_cd = ScalingFormulas.boss_fire_delay(level, 8.0, 3.0)
            if now - self.boss_state.last_spiral > spiral_cd and not spray_active:
                self.boss_charging_ability = True
                self.charge_start_time = now
                
                count = min(16, 12 + level // 15)
                for i in range(count):
                    angle = (i / count) * 2 * math.pi
                    self.spiral_lasers.append({
                        "x": self.boss_state.x,
                        "y": self.boss_state.y,
                        "angle": angle,
                        "speed": ScalingFormulas.projectile_speed(level, 150),
                        "rot_speed": 2
                    })
                self.boss_state.last_spiral = now
        
        # Wave attack (level 15+)
        if level >= 15 or is_super:
            wave_cd = ScalingFormulas.boss_fire_delay(level, 5.0, 2.0)
            if now - self.boss_state.last_wave > wave_cd and not spray_active:
                self.boss_charging_ability = True
                self.charge_start_time = now
                
                wave_count = ScalingFormulas.wave_count(level)
                if is_super:
                    wave_count = int(wave_count * 1.5)
                
                for i in range(wave_count):
                    angle = (i / wave_count) * 2 * math.pi
                    self.lasers.append({
                        "x": self.boss_state.x,
                        "y": self.boss_state.y,
                        "vx": math.cos(angle) * ScalingFormulas.projectile_speed(level, 300),
                        "vy": math.sin(angle) * ScalingFormulas.projectile_speed(level, 300)
                    })
                self.boss_state.last_wave = now
        
        # Rapid fire (level 30+)
        if level >= 30:
            rapid_cd = ScalingFormulas.boss_fire_delay(level, 10.0, 4.0)
            if now - self.boss_state.last_rapid > rapid_cd and not spray_active:
                self.boss_charging_ability = True
                self.charge_start_time = now
                
                rapid_count = min(30, 20 + level // 10)
                for _ in range(rapid_count):
                    angle = math.atan2(dy, dx) + (time.time() * 10) % (2 * math.pi) * 0.1
                    self.lasers.append({
                        "x": self.boss_state.x,
                        "y": self.boss_state.y,
                        "vx": math.cos(angle) * ScalingFormulas.projectile_speed(level, 500),
                        "vy": math.sin(angle) * ScalingFormulas.projectile_speed(level, 500)
                    })
                self.boss_state.last_rapid = now
        
        # FIX: Spray bullets (level 25+) - with lockout to prevent chaining
        if level >= 25:
            # Calculate cooldown - ensure it's always longer than total spray cycle
            base_spray_cd = ScalingFormulas.boss_fire_delay(level, 12.0, 6.0)
            
            # FIX: Check lockout AND cooldown
            lockout_ok = now >= self.spray_lockout_until
            cooldown_ok = now - self.boss_state.last_spray > base_spray_cd
            
            if lockout_ok and cooldown_ok and not self.chasing_laser:
                # Clear all projectiles
                self.lasers.clear()
                self.homing_missiles.clear()
                self.spiral_lasers.clear()
                self.boss_state.charging = False
                self.boss_state.returning_to_center = True
                
                # Set delays
                self.boss_state.last_laser = now + 2.0
                self.boss_state.last_rapid = now + 2.0
                self.boss_state.last_wave = now + 2.0
                self.boss_state.last_homing = now + 2.0
                self.boss_state.last_spiral = now + 2.0
                
                gap_to_player = math.atan2(py - self.boss_state.y, px - self.boss_state.x) + math.pi
                
                # FIX: Cap spray duration to prevent excessively long attacks
                spray_duration = 7.0 if not is_super else 9.0
                if level > 40:
                    spray_duration += min(3.0, math.log(level - 30))  # Cap at +3 seconds
                spray_duration = min(12.0, spray_duration)  # Hard cap at 12 seconds
                
                # FIX: Reduced grace period
                grace_period = 2.0  # Reduced from 3.5
                
                self.spray_bullets.append({
                    "start_time": now + 1.5,
                    "duration": spray_duration,
                    "angle": 0,
                    "gap_angle": gap_to_player,
                    "delay_end": now + 1.5,
                    "grace_period_end": now + spray_duration + grace_period + 1.5,
                    "rotation_speed": 15 + level * 0.2,
                    "level": level
                })
                
                # FIX: Set lockout to prevent immediate re-trigger
                # Lockout = spray_duration + grace_period + mandatory 3 second gap
                self.spray_lockout_until = now + spray_duration + grace_period + 1.5 + 3.0
                
                self.boss_state.last_spray = now
        
        # Chasing laser (level 35+)
        if level >= 35:
            chasing_cd = ScalingFormulas.boss_fire_delay(level, 15.0, 8.0)
            if now - self.boss_state.last_chasing > chasing_cd and len(self.spray_bullets) == 0:
                chasing_duration = 6.0 if not is_super else 8.0
                if level > 50:
                    chasing_duration += math.log(level - 40) * 0.5
                
                self.chasing_laser = {
                    "angle": math.atan2(py - 2000 - self.boss_state.y, px + 400 - self.boss_state.x),
                    "rot_speed": 0.75 + level * 0.01,
                    "start_time": now,
                    "duration": chasing_duration,
                    "width": 25
                }
                self.boss_state.last_chasing = now
        
        # Update boss charging animation
        if self.boss_charging_ability:
            charge_progress = min(1.0, (now - self.charge_start_time) / self.charge_duration)
            if charge_progress >= 1.0:
                self.boss_charging_ability = False
    
    def get_spray_active(self):
        """Check if spray attack is active"""
        return len(self.spray_bullets) > 0
    
    def can_player_shoot(self):
        """Check if player can shoot (grace period check)"""
        if len(self.spray_bullets) > 0:
            spray = self.spray_bullets[0]
            if time.time() < spray["grace_period_end"]:
                return False
        return True

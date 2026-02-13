"""
FILE: game/rendering.py
Complete rendering system with all visual effects - FIXED VERSION
Fixes:
- Boss projectiles now render ON TOP of player bullets for visibility
- Enhanced glow/outline effects on boss projectiles
- Increased projectile sizes for better visibility
"""

import pygame
import math
import time
import random

class Renderer:
    """Handles all game rendering with effects"""
    
    def __init__(self, screen):
        self.screen = screen
        self.font_big = pygame.font.Font(None, 60)
        self.font_med = pygame.font.Font(None, 40)
        self.font_small = pygame.font.Font(None, 30)
        self.font_tiny = pygame.font.Font(None, 24)
        
        # Cube vertices and edges
        self.verts = [
            [-1,-1,-1],[ 1,-1,-1],[ 1, 1,-1],[-1, 1,-1],
            [-1,-1, 1],[ 1,-1, 1],[ 1, 1, 1],[-1, 1, 1]
        ]
        self.edges = [(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7)]
    
    def render_game(self, game_state, player_state, boss_state, boss_ai, player, 
                   animation_manager, ability_manager, save_data):
        """Render main game screen - FIXED RENDER ORDER"""
        # FIX: Render player projectiles FIRST (bottom layer)
        self._render_player_projectiles(player, animation_manager)
        
        # Render boss
        self._render_boss(boss_state, boss_ai, player_state.x, player_state.y, game_state.level)
        
        # Render player
        self._render_player(player_state, save_data, ability_manager)
        
        # Render animations (middle layer)
        animation_manager.render(self.screen)
        
        # FIX: Render boss projectiles LAST (top layer) for visibility
        self._render_boss_projectiles(boss_ai, player_state)
        
        # Render HUD (always on top)
        self._render_hud(game_state, player_state, boss_state, save_data, ability_manager)
    
    def _render_boss_projectiles(self, boss_ai, player_state):
        """Render all boss projectiles with enhanced visibility effects"""
        # FIX: Enhanced laser rendering with glow and outline
        for laser in boss_ai.lasers:
            x, y = int(laser["x"]), int(laser["y"])
            # Outer glow (larger, semi-transparent feel via multiple layers)
            pygame.draw.circle(self.screen, (100, 30, 30), (x, y), 16)
            # Middle glow
            pygame.draw.circle(self.screen, (200, 50, 50), (x, y), 12)
            # Core (bright)
            pygame.draw.circle(self.screen, (255, 100, 100), (x, y), 8)
            # Inner highlight
            pygame.draw.circle(self.screen, (255, 200, 200), (x, y), 4)
        
        # FIX: Enhanced homing missiles with trail effect
        for missile in boss_ai.homing_missiles:
            x, y = int(missile["x"]), int(missile["y"])
            # Outer glow
            pygame.draw.circle(self.screen, (100, 60, 0), (x, y), 18)
            # Middle
            pygame.draw.circle(self.screen, (200, 120, 0), (x, y), 14)
            # Core
            pygame.draw.circle(self.screen, (255, 180, 50), (x, y), 10)
            # Trail line
            trail_x = int(x - math.cos(missile["angle"]) * 20)
            trail_y = int(y - math.sin(missile["angle"]) * 20)
            pygame.draw.line(self.screen, (255, 100, 0), (x, y), (trail_x, trail_y), 4)
            # Highlight
            pygame.draw.circle(self.screen, (255, 255, 150), (x, y), 5)
        
        # FIX: Enhanced spiral lasers with pulsing effect
        pulse = abs(math.sin(time.time() * 8)) * 0.3 + 0.7
        for spiral in boss_ai.spiral_lasers:
            x, y = int(spiral["x"]), int(spiral["y"])
            size = int(12 * pulse)
            # Outer glow
            pygame.draw.circle(self.screen, (80, 50, 150), (x, y), size + 6)
            # Middle
            pygame.draw.circle(self.screen, (150, 100, 255), (x, y), size + 2)
            # Core
            pygame.draw.circle(self.screen, (200, 180, 255), (x, y), size - 2)
        
        # Chasing laser (sweeping beam) - unchanged but enhanced
        if boss_ai.chasing_laser:
            start_x, start_y = boss_ai.boss_state.x, boss_ai.boss_state.y
            dx_laser = math.cos(boss_ai.chasing_laser["angle"])
            dy_laser = math.sin(boss_ai.chasing_laser["angle"])
            end_x = start_x + dx_laser * 2000
            end_y = start_y + dy_laser * 2000
            width = boss_ai.chasing_laser["width"]
            
            # Outermost glow
            pygame.draw.line(self.screen, (80, 30, 30), 
                           (int(start_x), int(start_y)), (int(end_x), int(end_y)), 
                           int(width * 2.0))
            # Outer layer
            pygame.draw.line(self.screen, (150, 50, 50), 
                           (int(start_x), int(start_y)), (int(end_x), int(end_y)), 
                           int(width * 1.5))
            # Middle layer
            pygame.draw.line(self.screen, (255, 80, 80), 
                           (int(start_x), int(start_y)), (int(end_x), int(end_y)), 
                           int(width))
            # Core (brightest)
            pygame.draw.line(self.screen, (255, 200, 200), 
                           (int(start_x), int(start_y)), (int(end_x), int(end_y)), 
                           int(width * 0.4))
    
    def _render_player_projectiles(self, player, animation_manager):
        """Render player bullets with trails"""
        for proj in player.projectiles:
            x, y = int(proj["x"]), int(proj["y"])
            if proj.get("nuclear"):
                pygame.draw.circle(self.screen, (0, 255, 0), (x, y), 10)
                pygame.draw.circle(self.screen, (0, 180, 0), (x, y), 6)
                if random.random() < 0.5:
                    animation_manager.spawn_particle(proj["x"], proj["y"], (0, 255, 0), 10, (0, 0))
            elif proj.get("explosive"):
                pygame.draw.circle(self.screen, (255, 100, 0), (x, y), 8)
                if random.random() < 0.5:
                    animation_manager.spawn_particle(proj["x"], proj["y"], (255, 150, 0), 15, (0, 0))
            elif proj.get("piercing"):
                pygame.draw.circle(self.screen, (255, 200, 0), (x, y), 6)
            else:
                pygame.draw.circle(self.screen, (50, 255, 50), (x, y), 6)
    
    def _render_boss(self, boss_state, boss_ai, player_x, player_y, level):
        """Render 3D cube boss with effects"""
        # Project vertices
        projected = []
        for v in self.verts:
            px, py = self._project_point(
                v[0] * 20, v[1] * 20, v[2] * 20,
                boss_state.x, boss_state.y,
                player_x, player_y
            )
            projected.append((px, py))
        
        # Determine color
        is_super = level % 10 == 0
        if is_super:
            color = (255, 0, 255)
            # Super boss glow
            glow_size = 65 + math.sin(time.time() * 4) * 5
            pygame.draw.circle(self.screen, color, 
                             (int(boss_state.x), int(boss_state.y)), int(glow_size), 3)
        elif boss_state.charging:
            color = (255, 120, 0)
        else:
            color = (70, 180, 255)
        
        # Boss charge animation
        if boss_ai.boss_charging_ability:
            charge_progress = min(1.0, (time.time() - boss_ai.charge_start_time) / boss_ai.charge_duration)
            charge_color = (255, 150 + int(105 * charge_progress), 0)
            pygame.draw.circle(self.screen, charge_color, 
                             (int(boss_state.x), int(boss_state.y)), 
                             int(60 + 40 * charge_progress), 4)
        
        # Draw edges
        for a, b in self.edges:
            pygame.draw.line(self.screen, color, projected[a], projected[b], 
                           6 if is_super else 5)
        
        # Draw face
        self._draw_face(projected, boss_state.emotion, is_super)
    
    def _project_point(self, x, y, z, cx, cy, mx, my):
        """3D projection"""
        dx = mx - cx
        dy = my - cy
        yaw = math.atan2(dx, 400)
        pitch = math.atan2(dy, 400)
        
        cos_yaw = math.cos(yaw)
        sin_yaw = math.sin(yaw)
        x1 = x * cos_yaw - z * sin_yaw
        z1 = x * sin_yaw + z * cos_yaw
        
        cos_pitch = math.cos(pitch)
        sin_pitch = math.sin(pitch)
        y1 = y * cos_pitch - z1 * sin_pitch
        z2 = y * sin_pitch + z1 * cos_pitch
        
        scale = 800 / (z2 + 400)
        return cx + x1 * scale, cy + y1 * scale
    
    def _draw_face(self, points, emotion, is_super=False):
        """Draw face on cube"""
        front = [points[i] for i in (0,1,2,3)]
        cx = sum(p[0] for p in front) / 4
        cy = sum(p[1] for p in front) / 4
        size = abs(front[1][0] - front[0][0]) * 0.7
        ex = size * 0.25
        ey = size * 0.18
        es = max(5, int(size * 0.12))
        
        if emotion == "super" or is_super:
            col = (255, 0, 255)
            pygame.draw.circle(self.screen, col, (int(cx-ex), int(cy-ey)), es+10)
            pygame.draw.circle(self.screen, col, (int(cx+ex), int(cy-ey)), es+10)
            pygame.draw.circle(self.screen, (255,255,0), (int(cx-ex), int(cy-ey)), es+5)
            pygame.draw.circle(self.screen, (255,255,0), (int(cx+ex), int(cy-ey)), es+5)
            pygame.draw.arc(self.screen, col, (cx-size*0.4, cy, size*0.8, size*0.5), 0, math.pi, 8)
        
        elif emotion == "normal":
            col = (255,255,0)
            pygame.draw.circle(self.screen, col, (int(cx-ex), int(cy-ey)), es)
            pygame.draw.circle(self.screen, col, (int(cx+ex), int(cy-ey)), es)
            pygame.draw.arc(self.screen, col, (cx-size*0.35, cy+size*0.1, size*0.7, size*0.35), 0, math.pi, 4)
        
        elif emotion == "angry":
            col = (255, 50, 50)
            pygame.draw.circle(self.screen, col, (int(cx-ex), int(cy-ey)), es+4)
            pygame.draw.circle(self.screen, col, (int(cx+ex), int(cy-ey)), es+4)
            pygame.draw.arc(self.screen, col, (cx-size*0.35, cy+size*0.2, size*0.7, size*0.3), math.pi, 0, 5)
        
        elif emotion == "hurt":
            for sx in (-ex, ex):
                pygame.draw.line(self.screen, (255,0,0),
                               (cx+sx-es, cy-ey-es), (cx+sx+es, cy-ey+es), 5)
                pygame.draw.line(self.screen, (255,0,0),
                               (cx+sx+es, cy-ey-es), (cx+sx-es, cy-ey+es), 5)
        
        elif emotion == "charging":
            col = (255,150,0)
            pygame.draw.circle(self.screen, col, (int(cx-ex), int(cy-ey)), es+8)
            pygame.draw.circle(self.screen, col, (int(cx+ex), int(cy-ey)), es+8)
            pygame.draw.arc(self.screen, col, (cx-size*0.4, cy, size*0.8, size*0.4), 0, math.pi, 8)
    
    def _render_player(self, player_state, save_data, ability_manager):
        """Render player cursor and effects"""
        px, py = int(player_state.x), int(player_state.y)
        
        # Idle bob
        py_draw = py + math.sin(time.time() * 3) * 2
        
        # Invincibility check
        is_invincible = player_state.invincible or (
            save_data["upgrades"]["voidwalker"] and player_state.voidwalker_timer < 5
        )
        
        # Determine color
        if is_invincible:
            color = (255, 255, 0)
            # Invincibility particles
            for i in range(4):
                angle = (i / 4) * 2 * math.pi + time.time() * 5
                vx = px + math.cos(angle) * 60
                vy = py_draw + math.sin(angle) * 60
                pygame.draw.circle(self.screen, (255, 255, 0), (int(vx), int(vy)), 8, 3)
        elif player_state.berserker_active:
            color = (255, 0, 150)
        elif player_state.hp > 30:
            color = (0, 255, 0)
        elif player_state.hp > 15:
            color = (255, 255, 0)
        else:
            color = (255, 0, 0)
        
        # Legendary ability effects
        if save_data["abilities"].get("chronoking", 0) > 0:
            aura_size = 80 + save_data["abilities"].get("chronoking", 0) * 10 + math.sin(time.time() * 3) * 5
            pygame.draw.circle(self.screen, (180, 180, 255), (px, int(py_draw)), int(aura_size), 2)

        # Singularity visual - pulsing purple repulsion field
        if save_data["abilities"].get("singularity", 0) > 0:
            stacks = save_data["abilities"].get("singularity", 0)
            sing_radius = 120 + stacks * 30 + math.sin(time.time() * 4) * 8
            pulse = abs(math.sin(time.time() * 5))
            alpha_color = (int(120 + 40 * pulse), 50, int(180 + 40 * pulse))
            pygame.draw.circle(self.screen, alpha_color, (px, int(py_draw)), int(sing_radius), 1)
            # Inner ring
            pygame.draw.circle(self.screen, (160, 80, 220), (px, int(py_draw)), int(sing_radius * 0.6), 1)

        # Chaos bargain visual - red damage glow
        if save_data["abilities"].get("chaos_bargain", 0) > 0:
            stacks = save_data["abilities"].get("chaos_bargain", 0)
            glow_intensity = int(80 + 30 * abs(math.sin(time.time() * 2)))
            pygame.draw.circle(self.screen, (glow_intensity, 20, 20), (px, int(py_draw)), 22 + stacks, 2)

        # Main cursor
        pygame.draw.circle(self.screen, color, (px, int(py_draw)), 15, 4)
        
        # Layered shields
        if player_state.titan_shield_active:
            pygame.draw.circle(self.screen, (200,150,255), (px, int(py_draw)), 55, 10)
            pygame.draw.circle(self.screen, (150,100,255), (px, int(py_draw)), 45, 8)
            pygame.draw.circle(self.screen, (100,180,255), (px, int(py_draw)), 35, 6)
        elif player_state.mega_shield_active:
            pygame.draw.circle(self.screen, (150,100,255), (px, int(py_draw)), 45, 8)
            pygame.draw.circle(self.screen, (100,180,255), (px, int(py_draw)), 35, 6)
        elif player_state.shield_active:
            pygame.draw.circle(self.screen, (100,180,255), (px, int(py_draw)), 35, 6)
        
        # Reflect charges
        if player_state.reflect_charges > 0:
            for i in range(player_state.reflect_charges):
                angle = (i / max(1, player_state.reflect_charges)) * 2 * math.pi + time.time()
                rx = px + math.cos(angle) * 50
                ry = py_draw + math.sin(angle) * 50
                pygame.draw.circle(self.screen, (255, 215, 0), (int(rx), int(ry)), 8, 3)
        
        # Parry
        if save_data["upgrades"]["parry"]:
            if player_state.parry_active:
                pygame.draw.circle(self.screen, (0, 255, 255), (px, int(py_draw)), 50, 5)
                pygame.draw.circle(self.screen, (0, 200, 255), (px, int(py_draw)), 42, 3)
            else:
                pygame.draw.circle(self.screen, (100, 200, 200), (px, int(py_draw)), 48, 2)
    
    def _render_hud(self, game_state, player_state, boss_state, save_data, ability_manager):
        """Render HUD elements"""
        # Player HP bar
        pygame.draw.rect(self.screen, (60,60,60), (20,20,300,25))
        hp_pct = player_state.hp / player_state.max_hp if player_state.max_hp > 0 else 0
        if hp_pct > 0.5:
            hp_color = (0,255,0)
        elif hp_pct > 0.25:
            hp_color = (255,200,0)
        else:
            hp_color = (255,0,0)
        pygame.draw.rect(self.screen, hp_color, (20,20,int(300 * hp_pct), 25))
        hp_text = self.font_small.render(f"HP: {int(player_state.hp)}/{int(player_state.max_hp)}", 
                                         True, (255,255,255))
        self.screen.blit(hp_text, (25, 55))
        
        # Level display
        is_super = game_state.level % 10 == 0
        level_text = f"Level {game_state.level}" + (" SUPER BOSS!" if is_super else "")
        level_color = (255,0,255) if is_super else (255,255,0)
        text = self.font_med.render(level_text, True, level_color)
        self.screen.blit(text, (280 if not is_super else 180, 20))
        
        # Boss HP bar
        pygame.draw.rect(self.screen, (60,60,60), (480,20,300,25))
        boss_hp_pct = boss_state.hp / boss_state.max_hp if boss_state.max_hp > 0 else 0
        if boss_hp_pct > 0.6:
            boss_color = (255, 100, 100)
        elif boss_hp_pct > 0.3:
            boss_color = (255, 150, 0)
        else:
            boss_color = (255, 50, 50)
        pygame.draw.rect(self.screen, boss_color, (480,20,int(300 * boss_hp_pct), 25))
        boss_text = self.font_small.render(f"BOSS: {int(boss_state.hp)}", True, (255,255,255))
        self.screen.blit(boss_text, (485, 47))
        
        # Status indicators
        status_y = 90
        is_invincible = player_state.invincible or (
            save_data["upgrades"]["voidwalker"] and player_state.voidwalker_timer < 5
        )
        
        if is_invincible:
            status_text = self.font_tiny.render("INVINCIBLE!", True, (255,255,0))
            self.screen.blit(status_text, (600, status_y))
            status_y += 25
        
        if player_state.berserker_active:
            status_text = self.font_tiny.render("BERSERKER MODE!", True, (255,0,150))
            self.screen.blit(status_text, (600, status_y))
            status_y += 25
        
        # Movement hint
        if save_data["settings"]["movement"] == "arrows":
            hint = self.font_tiny.render("WASD/Arrows to move", True, (150,150,150))
            self.screen.blit(hint, (20, 580))
        
        # Ability icons
        self._render_ability_hud(ability_manager)
    
    def _render_ability_hud(self, ability_manager):
        """Render ability cooldown display"""
        hud_x = 20
        hud_y = 100
        slot = 0
        now = time.time()
        
        for ability_name, ability in ability_manager.player_abilities.items():
            if ability.key is None:
                continue
            
            x = hud_x + slot * 60
            y = hud_y
            
            # Background
            pygame.draw.rect(self.screen, (40,40,40), (x, y, 48, 48))
            
            # Rarity border
            rarity_color = ability_manager.RARITY_COLORS.get(ability.rarity, (255,255,255))
            pygame.draw.rect(self.screen, rarity_color, (x, y, 48, 48), 2)
            
            # Key label
            key_name = pygame.key.name(ability.key).upper()
            key_text = self.font_tiny.render(key_name, True, (255,255,255))
            self.screen.blit(key_text, (x+18, y+16))
            
            # Cooldown arc
            if ability.cooldown > 0:
                elapsed = now - ability_manager.last_used.get(ability_name, -999)
                cd = ability.get_cooldown()
                if elapsed < cd:
                    ratio = elapsed / cd
                    angle = ratio * 2 * math.pi
                    pygame.draw.arc(self.screen, (0,200,255), (x-2, y-2, 52, 52),
                                  -math.pi/2, -math.pi/2 + angle, 4)
                else:
                    pygame.draw.rect(self.screen, (0,255,0), (x, y, 48, 48), 2)
            
            slot += 1

        # Render passive ability indicators below active ones
        passive_x = hud_x
        passive_y = hud_y + 58
        for ability_name, ability in ability_manager.player_abilities.items():
            if ability.key is not None:
                continue
            rarity_color = ability_manager.RARITY_COLORS.get(ability.rarity, (255,255,255))
            # Small passive indicator
            pygame.draw.rect(self.screen, (30, 30, 30), (passive_x, passive_y, 36, 20))
            pygame.draw.rect(self.screen, rarity_color, (passive_x, passive_y, 36, 20), 1)
            label = ability_name[:4].upper()
            text = self.font_tiny.render(f"{label}x{ability.stacks}", True, rarity_color)
            self.screen.blit(text, (passive_x + 2, passive_y + 2))
            passive_x += 42

"""
FILE: game/animations.py
Complete animation management with all visual effects
"""

import pygame
import math
import random
import time
from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class Animation:
    """Single animation instance"""
    kind: str
    x: float
    y: float
    lifetime: float
    age: float = 0.0
    data: Dict[str, Any] = field(default_factory=dict)
    
    def update(self, dt: float) -> bool:
        """Returns False when animation is done"""
        self.age += dt
        return self.age < self.lifetime
    
    def get_progress(self) -> float:
        """0.0 to 1.0"""
        return min(1.0, self.age / self.lifetime)

class AnimationManager:
    """Centralized animation system with all effects"""
    
    def __init__(self):
        self.animations: List[Animation] = []
        self.particles: List[List] = []
        self.trail: List[List] = []
        self.hit_flash: List[List] = []
        self.teleport_flash: List[List] = []
        
        # Screen shake
        self.screen_shake_intensity = 0
        self.screen_shake_duration = 0
        self.screen_shake_start = 0
    
    def spawn(self, kind: str, x: float, y: float, lifetime: float = 0.5, **data):
        """Create new animation"""
        self.animations.append(Animation(kind, x, y, lifetime, 0.0, data))
    
    def spawn_particle(self, x: float, y: float, color: tuple, lifetime: int = 30, speed: tuple = (0, -2)):
        """Spawn particle effect"""
        self.particles.append([x, y, speed[0], speed[1], color, lifetime])
    
    def add_trail(self, x: float, y: float):
        """Add trail point"""
        if len(self.trail) < 50:
            self.trail.append([x, y, 0])
    
    def trigger_teleport(self, x: float, y: float):
        """Teleport visual effect"""
        self.teleport_flash.append([x, y, 0])
        for _ in range(16):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(3, 8)
            self.spawn_particle(x, y, (120, 200, 255), 25, 
                              (math.cos(angle) * speed, math.sin(angle) * speed))
        self.screen_shake(8, 0.2)
    
    def enemy_hit_effect(self, x: float, y: float):
        """Enemy hit visual"""
        self.hit_flash.append([x, y, 0])
        for _ in range(8):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(2, 5)
            self.spawn_particle(x, y, (255, 100, 100), 20, 
                              (math.cos(angle) * speed, math.sin(angle) * speed))
    
    def screen_shake(self, intensity: int = 5, duration: float = 0.3):
        """Trigger screen shake"""
        self.screen_shake_intensity = intensity
        self.screen_shake_duration = duration
        self.screen_shake_start = time.time()
    
    def get_shake_offset(self) -> tuple:
        """Get current shake offset"""
        if time.time() - self.screen_shake_start < self.screen_shake_duration:
            return (random.randint(-self.screen_shake_intensity, self.screen_shake_intensity),
                   random.randint(-self.screen_shake_intensity, self.screen_shake_intensity))
        return (0, 0)
    
    def update(self, dt: float):
        """Update all animations"""
        # Update main animations
        self.animations = [anim for anim in self.animations if anim.update(dt)]
        
        # Update particles
        for p in self.particles[:]:
            p[0] += p[2]
            p[1] += p[3]
            p[5] -= 1
            if p[5] <= 0:
                self.particles.remove(p)
        
        # Update trail
        for t in self.trail[:]:
            t[2] += 1
            if t[2] > 12:
                self.trail.remove(t)
        
        # Update hit flash
        for fx in self.hit_flash[:]:
            fx[2] += 1
            if fx[2] > 10:
                self.hit_flash.remove(fx)
        
        # Update teleport flash
        for fx in self.teleport_flash[:]:
            fx[2] += 1
            if fx[2] > 10:
                self.teleport_flash.remove(fx)
    
    def render(self, screen: pygame.Surface):
        """Render all animations"""
        # Render particles
        for p in self.particles:
            pygame.draw.circle(screen, p[4], (int(p[0]), int(p[1])), 3)
        
        # Render trail
        for t in self.trail:
            pygame.draw.circle(screen, (200, 200, 255), (int(t[0]), int(t[1])), 6)
        
        # Render hit flash
        for fx in self.hit_flash:
            pygame.draw.circle(screen, (255, 0, 0), (int(fx[0]), int(fx[1])), 16 - fx[2])
        
        # Render teleport flash
        for fx in self.teleport_flash:
            pygame.draw.circle(screen, (120, 200, 255), (int(fx[0]), int(fx[1])), fx[2] * 4, 3)
        
        # Render main animations
        for anim in self.animations:
            if anim.kind == "explosion":
                self._render_explosion(screen, anim)
            elif anim.kind == "particle":
                self._render_particle(screen, anim)
            elif anim.kind == "hit_flash":
                self._render_hit_flash(screen, anim)
            elif anim.kind == "charge_warning":
                self._render_charge_warning(screen, anim)
            elif anim.kind == "teleport_flash":
                self._render_teleport_flash(screen, anim)
    
    def _render_explosion(self, screen: pygame.Surface, anim: Animation):
        progress = anim.get_progress()
        radius = int(anim.data.get("max_radius", 40) * progress)
        color = anim.data.get("color", (255, 180, 0))
        if radius > 0:
            pygame.draw.circle(screen, color, (int(anim.x), int(anim.y)), radius, 4)
    
    def _render_particle(self, screen: pygame.Surface, anim: Animation):
        color = anim.data.get("color", (255, 255, 255))
        pygame.draw.circle(screen, color, (int(anim.x), int(anim.y)), 3)
    
    def _render_hit_flash(self, screen: pygame.Surface, anim: Animation):
        progress = anim.get_progress()
        radius = max(1, int(20 - progress * 15))
        color = (255, 0, 0)
        pygame.draw.circle(screen, color, (int(anim.x), int(anim.y)), radius)
    
    def _render_charge_warning(self, screen: pygame.Surface, anim: Animation):
        progress = anim.get_progress()
        radius = int(60 + progress * 120)
        color = (255, int(255 * (1 - progress)), 0)
        if radius > 0:
            pygame.draw.circle(screen, color, (int(anim.x), int(anim.y)), radius, 4)
    
    def _render_teleport_flash(self, screen: pygame.Surface, anim: Animation):
        progress = anim.get_progress()
        radius = int(progress * 40)
        color = (120, 200, 255)
        if radius > 0:
            pygame.draw.circle(screen, color, (int(anim.x), int(anim.y)), radius, 3)
